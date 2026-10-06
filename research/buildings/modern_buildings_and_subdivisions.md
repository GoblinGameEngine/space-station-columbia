# Modern buildings and subdivisions — research notes

Saved 2026-09-30 from sessions on 2026-09-29. These notes were kept so the research isn't lost; work
hasn't started. Proposed feature: new modern/futuristic residential subdivisions and retail/commercial
buildings, placed as new settlements in the countryside. They'd be built through the existing
catalog/gen pipeline, with construction "tokenized" so the parts (walls, roofs, windows,
storefronts...) combine procedurally into many variations instead of one-off buildings.

## Where the research came from

The image and floor-plan collection was put together by the Claude session on the user's Windows PC,
not on the laptop. The files are still only on that machine:

`C:\Users\test-13600\Games\SpaceStationColumbia\house_reference_library\`

- 30 exterior and interior images, from Pexels, Wikimedia Commons, and current Toll Brothers and
  Lennar model-home renders.
- 8 real builder floor plans (SVG): Lennar Eleanor and Kimball; Toll Brothers Bella, Radiant, Satin
  and AFY.
- `NOTES.md`, the design-language summary condensed below.

**Sources:** the per-image URLs are in that folder's `NOTES.md` on the Windows PC. They weren't
relayed to the laptop, so they're not reproduced here. TODO: copy `NOTES.md` (with its links) and
the reference files into this folder.

## Style intent

A deliberate departure from the game's existing vernacular-Americana catalog: genuinely
modern/futuristic, as a contrast. Think "model home of the future" showcase subdivisions, not a
stylistic fit with the rest of the world.

## Design language (from the Windows session's NOTES.md)

- Massing: stacked rectangular volumes at 2–3 roof heights.
- Materials: about 3 at most. A warm stucco field, a dark metal accent, and wood or stone used
  sparingly.
- Roofs: flat or low-slope with parapets, or simple gables. Deep overhangs.
- Glazing: oversized, frameless glass on the living facades; punched windows elsewhere.
- The rear facade matters as much as the front: a glass wall, a covered patio, a pool.
- Plans: 4–5 bedrooms and 3.5–5 baths, open concept, split-bedroom layout, 2–3 car garage.

## How it maps onto the existing pipeline (repo investigation, 2026-09-29)

Buildings are already trait-driven procedural builds, not bespoke meshes:

- `remake/catalog/<ID>.json` (about 1,707 records): each record describes a real example as traits.
  The schema is in `remake/research/CATALOG_SPEC.md`.
- `remake/blender/build_record.py`: dispatches on the record's `kind` via `GENERATORS`. New kinds
  (for example `house_modern`, `store_modern`) would slot in here.
- `remake/blender/gen/common.py`: per-record seeded rng, `Palette`, `std_materials`, `sign_board`,
  and the tinted "lib" texture set.
- `remake/blender/gbhouse.py`: a declarative `House` spec (blocks, rooms, doors, windows, stairs,
  porches, chimneys) turned into geometry. Flat roofs with parapet and coping already exist
  (about lines 570–583).
- `remake/blender/gblib.py`: the parts library (walls with openings, windows, doors, roofs, stairs,
  rails, columns, lintels, transoms, text).
- `remake/blender/gen/house.py`: turns traits into a plan (side-hall, one-storey, shotgun, attic,
  towers, yard, garage).
- Commercial: `gen/store.py` and `gen/works.py` already handle store, restaurant, market, bigbox and
  strip. `bigbox` and `strip` have only about 2 records each. `gen/shopfit.py` is a reusable
  storefront fixture kit.
- Placement: `Town.subdivision(uc, vc, a, b, connect, spacing)` in `tools/map_expanded.py` already
  generates a cul-de-sac loop with house footprints. `bld(poly, kind)` accepts any kind string.

### Gaps

- No real glass material: in `common.py`'s `WALL_TEX`, the trait values `glass_modern` and
  `glass_curtain` fall back to plain stucco. There's no glass or curtain-wall texture in
  `remake/textures/lib`.
- Unresolved: where a map footprint's `kind` resolves to a specific catalog record ID for
  instancing. Possibly `remake/inventory/map_inventory.json` (referenced in `common.py`) or another
  `tools/` script.
- `research/building_catalog/` has no modern/upscale archetypes yet. New entries should follow its
  `_catalog_index.md` template.

## Build notes for a fresh clone (laptop, 2026-09-28)

- The project needs Godot 4.7.
- `remake/tools/build_all.sh` fails on a fresh clone because `godot_project/remake/buildings/`
  doesn't exist. Create it first.
- `road_signs.png` comes from `tools/sign_atlas.py`, which `build_all.sh` doesn't run.
