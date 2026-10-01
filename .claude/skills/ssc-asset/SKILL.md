---
name: ssc-asset
description: Make a 3D game asset for Space Station Columbia (a vehicle, cart, boat, machine or prop) from Grok 2D reference images to a rigged, textured GLB in the game, fast and accurate. Use when asked to create, model, rebuild or add any SSC asset or model, or to work on tools/assets or remake/blender.
---

# SSC assets: Grok references to a model in the game

**The user's rule:** Grok makes **2D reference images only**; models and textures are made here, in Blender, from those images. No asset work happens without a go-ahead (reference images included).

## The pipeline (speed first: batch everything, parallel everywhere)
1. **Catalogue.** Add or confirm the asset in `tools/assets/catalog.py`:
   - its family: `hull` (solid body), `transit` (hull plus a furnished interior), `frame` (open or wiry, built part by part), or `existing`;
   - a one-line `look` in the station's design language: 1970s retro-futurist, soft rounded corners, cream, chrome and muted colours, round lamps; electric or pedal only, so no grille, exhaust or fuel cap;
   - the views it needs.
   Real sizes come from `godot_project/remake/characters/npc_vehicles.json` (`size_m` = L, W, H). Anything that isn't a vehicle needs a size entry first.
2. **References:** `python3 tools/assets/grok_refs.py <ids> --workers 6`.
   - The master side elevation is made with `image_gen`; every other view is made with `image_edit` from the master's absolute path, one Grok call per view, so files are labelled exactly.
   - Images go to `reference/grok/<id>/<view>.jpg` (gitignored).
   - About 6 s and $0.02 per image; 6 workers is fine.
3. **Review the references:** `python3 tools/assets/sheet.py <ids> -o <scratch>/x.png`, then read the sheet.
   - Check the views are the same object, the background is flat, and the side view is truly side-on.
   - Regenerate one view with `--force --views front`.
4. **Measure:** `~/.venvs/ssc-assets/bin/python tools/assets/analyze.py <ids> [--debug]`. It produces:
   - silhouettes, keyed off the grey background;
   - outlines in metres, scaled from `size_m`;
   - wheels, fitted to the silhouette's bottom edge (one per ground-contact patch, equal radii snapped);
   - colours;
   - a JPEG atlas with the background bled out.
   `--debug` writes `_dbg_<view>.jpg` with the detected wheels drawn on.
5. **Build:** `python3 tools/assets/build.py <ids> --workers 4 --sheets` writes `godot_project/remake/vehicles/<id>.glb`, renders, side overlays, and `reference/grok/_review_*.png`.
   - **hull** (`remake/blender/kit/hull.py`): the body is the intersection of the side, front, rear and top silhouettes extruded through it. The atlas is projected by face normal (side, front, rear, top). Faces pointing up with no top view sample the body colour just below the outline. Rigged wheels `wheel_<F|B|M#><L|R>` carry the drawn hubcaps.
   - **frame** (`remake/blender/assets/<id>.py`, a `build(an, out, render)`): parts from `kit.core.Mesh` (pipe, lathe, box, quad_strip), dimensions from the analysed side and front views. See `remake/blender/vehicles/bicycle.py` for the full example.
   - **transit** (`remake/blender/kit/transit.py`): the hull hollowed under its roof line (`SHELL` thick, the inside faces given the lining), window openings cut one at a time, then the interior as Grok drew it (below), doors, rider markers. The build prints `CLEARANCE`: floor to ceiling must be at least 2.2 m everywhere in the passenger area (the user's rule); the passenger area is shortened where the roof comes down.
   - **articulated** (CFG `joints`, fractions of the length): cut into sections and 1.2 m joint modules alternating (`body_0` front .. `body_N`), a `GAP` at every pivot, `pivot_lead`/`pivot_trail` empties per body (nose, joints, tail), one `bellows_rib` mesh. In the game (`transit_vehicle.gd`) the bodies follow the road like trailers (each trail pivot on the line a body length behind its lead), no joint bends past `MAX_BEND` (24°, where the corners would meet), ribs are strung across each gap, and each body gets a collider. More, shorter sections take tighter corners: a joint bends about (section/2 + module/2) / radius.
6. **Verify (accuracy).** Read the review sheet.
   - The side overlay (render at 50% over the reference) must line up: outline, wheels, height.
   - The three-quarter render must read as the reference's three-quarter view.
   - Fix by adjusting the analysis (scale, wheels) or the builder, never by eye in the game.
7. **In the game.** For a spot check, `godot4 --headless --path godot_project --import`, then place the model with DevBridge (`tools/gcmd.py run`) and screenshot. Tell the user before restarting the game or moving the player.
8. **Commit:** the `.glb`, any extracted `.png` textures, scripts and catalogue. Never commit `.import` files or anything in `reference/`.

## Interiors (anything people ride inside)
- Catalogue views `TVI`: the hull set plus `interior_section` (cutaway side elevation), `interior_plan` (roof off, from above), `interior_aisle` (down the aisle) and `interior_layout` (the plan redrawn as a flat colour-coded diagram: seats red, backrests blue, doorways green; an edit of the plan, for exact measuring).
- `~/.venvs/ssc-assets/bin/python tools/assets/interior.py <ids> --debug` writes `reference/grok/<id>/interior.json`: seat rows from the plan (`rows`: y, left?, right?), colours from the aisle view (seat, floor, ceiling, wall), and `floor.jpg` cut from the plan's aisle. `_dbg_interior.jpg` shows what it found.
- The build renders `r_aisle.png` from the back of the cabin: hold it against Grok's `interior_aisle.jpg`.

## Conventions (the game's contract)
- **Axes and units:** Blender Z up, front toward +Y (Godot forward -Z after the glTF export), X to the right; metres; z = 0 at the ground (wheels or keel).
- **Rig names:** `wheel_*` spin about local X; `steer` turns about its local Z; `door_*`, `seat_*`, `grip_L/R`, `pedal_L/R`, `seat_rider`, `stand_*` and `exit_*` are empties or parts the game reads.
- **Textures:** the reference atlas (hull and transit), or numpy-drawn textures packed into the GLB (frame).

## Review checks on the references (do them every batch: tile all side views into one grid and read it)
- **Facing.** The front must point right. Grok draws about 1 in 14 facing left (trailers, hearse, stroller, harrow, kiddie train...). Add those ids to `analyze.FLIP`, which mirrors the side and top views before measuring.
- **Perspective.** The side view must be truly flat. A three-quarter-ish side view (the first transit bus, with a stray wheel under the door) gets regenerated with `grok_refs.py <id> --force`.
- **Proportions.** Grok often draws long vehicles stubby. `analyze.py` keeps the drawing's proportions when its implied height is within 15% of `size_m`, and otherwise scales the height separately (`scale_y` / `scale_z`).
- **Batch errors.** About 3% of edits fail with transient image-service errors. Re-running `grok_refs.py` fills only the missing views.

## Pitfalls (each cost time once)
- **White or pale bodies** key out in pieces on the grey background. `analyze.py` closes the gaps and fills solid (inside = silhouette above, below, left and right), but a white box trailer still failed: give pale subjects a colour in their `look` and regenerate.
- **A view that empties the hull** (bad outline): `hull.py` skips any view whose intersection collapses the body (any dimension under 60%) and logs `HULL_WARN`.
- **Overlapping window boxes** wreck the boolean: cut them one at a time and skip a cut that destroys the shell.
- **The front view's width includes the mirrors**: size anything inside from the narrowest half-width over the cabin's height.
- **Window panes** come out fragmented; the lining's openings merge panes into bays (gaps under 0.4 m).
- **Grok credit**: an exhausted account answers "402 Payment Required: Grok Build usage balance exhausted"; every job then fails fast. Tell the user; nothing to retry.
- **Blender is a Flatpak:** it can't write to `/tmp/claude-*`. Write under `/home/deck` (`reference/grok/<id>/build`).
- **Parenting in bpy:** call `bpy.context.view_layer.update()` before setting `matrix_parent_inverse` (`kit.core.attach` does this).
- **Boolean meshes** come back with an empty material slot: `me.materials.clear()` before assigning.
- **Grok** ignores "no grille" about half the time. That's acceptable as styling.
- **Image models garble text,** so ask for none and draw signs and badges in code.
- **Wheel detection:** a hull with a flat bottom (boats, skirts) has no contact patches, which is correct: no wheels.
- **Analysis libraries:** scipy and OpenCV live only in the venv (`~/.venvs/ssc-assets`), not in system Python or Blender.
- **Cutout (frame) wheels:** spinning wheels are added only when detection is plausible (2-4 wheels spread over 35% of the length). Otherwise the drawn wheels stay on the panels; training wheels fool detection.
- **Transit windows:** detected as pale, low-chroma regions near the background tone. Cream paint can pass the test, so oversized "windows" are rejected (over 30% of the length or 45% of the height), with a configured window band as the fallback. End windscreens are never cut.
