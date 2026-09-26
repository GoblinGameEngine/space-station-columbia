# Space Station Columbia

A first-person game set inside Space Station Columbia: an O'Neill cylinder 3 km in radius and 8 km
long. Its floor holds a research-derived American landscape, with towns, farms, rivers, a lake,
two seas and a railway. You can walk it, drive its ground vehicles or fly its aerostats. The
NYNEX Communicator, a mid-90s PDA running "The System", is the menu.

Forked from Goblin Engine on 2026-09-25. The engine's agent tooling (`tools/gcmd.py` talking to the
in-game `DevBridge.gd`) is how the game is built and tested.

## License

All rights reserved for now (see `LICENSE`) — this repo is public so
it's visible and testable, not because it's open source yet. A
permissive license is planned once the project reaches a usable state.

## Version

**Current: `0.6.1-prealpha.14`** — pre-alpha. Tracked in the `VERSION`
file at the repo root (single source of truth) and mirrored into
`godot_project/project.godot`'s `config/version`.

Scheme: `MAJOR.MINOR.PATCH-phase.N`, phase one of `prealpha` / `alpha`
/ `beta` / `rc`, dropped entirely at `1.0.0` (first real release):
- `MAJOR.MINOR.PATCH` bumps like normal SemVer — patch for fixes, minor
  for new features, major reserved for 1.0.0 and later breaking changes.
- `N` is a counter within the current phase, bumped on each tagged push
  during that phase (`prealpha.1`, `prealpha.2`, ...).
- Advancing phases (e.g. pre-alpha → alpha) resets `N` to `1` and is a
  deliberate call, not automatic — currently pre-alpha until told
  otherwise.

Each versioned push is tagged in git as `v<version>` (e.g. `v0.1.0-prealpha.1`).

## Repo layout

- `godot_project/` — the Godot 4.3 project. The main scene is `remake/scenes/RemakeStation.tscn`.
  - `remake/`: the station's data (terrain, placement, roads, vehicles), its buildings (`buildings/`,
    built from the catalog) and its textures.
  - `scripts/world/`: the world systems (MapTerrain, MapRoads, RoadFurniture, MapWater, MapTrees,
    GreatBridges, CoastalWalks, CliffWalls, DaySkySystem, StationGeo...).
- `remake/`: the building pipeline. It has the catalog records, the Blender generators, the checks and
  the reference photos.
- `tools/`: the map and road generators (`map_expanded.py`, `road_network.py`, `road_furniture.py`,
  `sign_atlas.py`) and `gcmd.py`, the DevBridge client.
- `research/`: the research the map, the buildings and the road standard are built from.

## GitHub

Repo: **https://github.com/GoblinGameEngine/space-station-columbia** (public)

Pushed with `gh` CLI, authenticated as the `GoblinGameEngine` account.

`.gitignore` excludes, deliberately:
- `/reference/` — personal photos and character-reference images used
  as source material while building assets, not meant to be published.
  Kept local-only.
- `godot_project/.godot/` — Godot's editor cache/import artifacts,
  fully regenerated automatically on next open.
- `godot_project/build/` — exported game binaries, regenerate via
  Godot's export, not source.
- `*.blend1` / `*.blend2` — Blender autosave backups.
- `/godot/` — a spare local copy of the Godot engine binary, not
  project code.

Everything else (scripts, scenes, textures, `.blend` project files,
tools) is committed.

### Git identity

This repo's commits use `GoblinGameEngine <GoblinGameEngine@users.noreply.github.com>`
as the author, set locally for this repo only — it does not affect your
global git config or any other project.

### Pushing future changes

```bash
cd ~/goblin-engine
git add -A
git commit -m "..."
git push
```
