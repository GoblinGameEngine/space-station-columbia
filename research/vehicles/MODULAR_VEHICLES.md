# Modular vehicles: platform, tube frame, panels

How every vehicle in Space Station Columbia is built, from the road tram on. The rules here are the
user's (2026-10-01) and are hard rules; the method is what was learned building the Carrow tram, written
down so the next vehicle takes a fraction of the time.

## 1. Construction (canon and code)

Every vehicle has three layers:

1. **The platform.** A Steward skateboard board (`remake/blender/vehicles/...`, `steward_tram.glb`) carries the
   wheels, motors, battery and steering. It is the Steward's work, the same everywhere.
2. **The frame.** A welded tube space frame, bolted to the board at its sills and floor. This is the
   human makers' craft. Harrow, Carrow and Solana are cottage industries, skilled and replicable, in the
   tradition of the British tube-frame builders: the Lotus Seven and the Caterham and Westfield that
   followed, TVR, Ginetta, and the Ariel Atom (whose frame is its look).
3. **The panels.** Exterior panels (the skin) and interior panels (linings, ceilings, end walls) are
   fastened to the frame. Glazing and doors sit in the openings. Seats and fittings bolt to the floor
   and walls.

The rules:

- **Modular within a class.** A component fits every vehicle of its class whatever the maker's style,
  and never a vehicle of another class. The class standard (section 2) fixes the dimensions; the style is
  free inside them.
- **Sealed.** The exterior panels join at every edge into one closed skin, and the interior panels into
  another. At every window and door opening the two shells join (the reveal). There are no gaps, ever:
  as built and while the frame is bent.
- **The frame stays hidden.** It is never visible from outside, unless a style shows it on purpose (listed
  in the standard's `tubes.exposed_outside`). From inside it may be minimally visible. When a panel falls
  off, the frame behind shows.
- **Damage.** An impact bends the frame. Panels whose mounts are strained past their tolerance come off.
  Glass shatters. Fallen panels are physics bodies with their dented shape.

## 2. The class standard

`remake/blender/kit/standards.py`, written to `godot_project/remake/vehicles/standards/<id>.json`. One per
class. RT255 is the road tram: 2.55 m wide, 8.4 m between portals, on the Steward tram board.

A standard fixes:

- **The fixed heights and widths:** deck, floor, skirt, belt, window band, cant rail, crown; the door
  aperture; the portal.
- **The two shells' profiles:** the exterior skin's half width up the side and shoulder (`exterior`), and
  the interior lining, cove and ceiling (`interior`).
- **The frame:**
  - the ring's joints (`ring`, at the cavity centrelines between the shells);
  - which joints are bolted to the board;
  - the stringers;
  - the tube sizes;
  - the end-hoop inset.
- **The slots:** the side is a run of `end`, `door`, `bay_short` and `bay_long` slots, plus 1.4 m roof
  slots. A component declares the slot it fills.
- **Tolerance per role:** how much mount strain each part takes before it comes off.
- **The steel:** yield strain, plasticity, dent energy, maximum dent.

The **interface key** `standard/role/slot/side` is the compatibility rule: components with equal keys
swap.

## 3. Component roles

| layer | roles |
|---|---|
| exterior | `side_bay`, `door_head`, `roof_bay`, `end_portal`, `end_cap`, `wheel_well` |
| interior | `lining_bay`, `door_head_lining`, `ceiling_bay`, `end_lining`, `cap_lining`, `floor`, `podium` |
| joints | `reveal` (round every window, door and portal: part of both shells) |
| closers | `glazing`, `door_glass`, `door_leaf` (and `ramp`, outside) |
| fittings | `seat`, `stanchion`, `fittings`, `cab`, `roof_fairing` |

## 4. Building a vehicle (the builder script)

The tram is `remake/blender/tram/carrow_tram.py`; copy its structure.

1. **Profiles first.** Define one profile per shell: `ext_x(z)` (piecewise linear) and `int_x(z)`, which
   is the polyline through `INT_Z` on the cove, never the true curve.
2. **Cut everything from those profiles on the same breakpoints.**
   - `skin(mid, side, y0, y1, holes, outer)` makes a panel as a quad grid with the holes cut out.
   - `reveal()` makes the return round each hole, from the skin to the lining. It is its own component.
   - `sill_pan()` closes the exterior to the platform.
   - `wheel_well()` lines each arch.
   - `end_panels()` makes the outer end panel, the inner end wall, the portal reveal and the bulkhead.
   - A cap is an exterior loft plus a lining loft from `interior_loop()`. Each loft is joined to its face
     border with `zipper()`.
3. **Label every module.** Give it a module kind (mapped to a role), its slot via `SLOT[mid]` (or "free"),
   and hit points, mass, how it breaks, and collision boxes.
4. **Export.** `kit/components.Library` exports the modules as components in their slot's frame (deduped),
   writes the pack and catalog, and the builder writes a blueprint per vehicle part: placements, doors,
   markers, stations.
5. **Test** (section 6). Fix what fails, rebuild, repeat until both pass.

## 5. In the game

| class | file | does |
|---|---|---|
| VehicleLibrary | `remake/scripts/vehicles/body/vehicle_library.gd` | catalogs, packs, materials (double-sided), `compatible(interface)` |
| TubeFrame | `remake/scripts/vehicles/body/tube_frame.gd` | the frame from standard + blueprint; skin binding; `impact()` dents with plastic set; `strain()` |
| VehicleBody | `remake/scripts/vehicles/body/vehicle_body.gd` | `prepare()` (worker thread, cached, warmed at load); `make()`; `impact()`; `break_off()` (debris / shards) |

**Drawing.**
- Every fixed component is bound to the frame's joints and merged per material into one skinned mesh on
  a Skeleton3D whose bones are the joints. That is about 30 draws a section, and the GPU bends it.
- Moving parts (door leaves, door glass, ramps) are their own nodes.
- The tubes are drawn inside the cavity, so they show only where a panel is gone.

**Binding.** A point is bound by its angle round the ring's middle, bilinearly between the two rings
either side. The weights are continuous in position, so coincident seam vertices always move together and
a bent body keeps its seams closed.

**Damage.** `TramSection.knock_from` sends energy to `bend()`:
1. the frame dents (joints near the blow pushed in, then relaxation, then plastic set past yield);
2. the skin follows the bones;
3. the collision boxes follow;
4. parts strained past tolerance break off.

## 6. The tests (run after every rebuild)

`tools/vehicle_seal_test.py` assembles the body from the blueprint exactly as the game does.

- **Seal.** Rays from points throughout the cabin (clear of the wheel housings) are cast against the
  exterior shell alone, then against the interior shell alone. Closers and reveals count in both; the
  platform closes the bottom; the portals are allowed. Both shells must report SEALED. For the dense run
  use `SEAL_DIRS=2400 SEAL_ROWS=11`.
- **Tubes** (`TUBES=1`). Points on every tube's surface cast rays against everything opaque. Glass is
  see-through, and the portal is allowed. Nothing may be seen from outside.

## 7. Lessons (what cost time on the tram)

- **Seams.** A reveal cut on the true cove curve, against a lining cut on chords, left a hairline gap. Cut
  everything from the polyline.
- **Mirroring.** Mirroring a half profile dropped the end point and opened a gap the whole length of the
  roof. Build arcs explicitly, from one end to the other.
- **Caps.** Different vertex sets on the same outline leave slivers; zip them.
- **Backfaces.** Hand-built faces have mixed winding, so use double-sided materials.
- **Frame clearance.** Tubes cross openings unless the frame builder knows them: doors, windows and
  arches are openings. Step jamb hoops back from the aperture, inset the end hoops, put no hoops in
  moulded caps, and run the floor members inside the floor slab.
- **Test design.** Sample points must be inside the cabin. In the tube test every opaque panel occludes.
- **Engine gotchas.**
  - Jolt rebuilds a compound shape per added child: add the shapes first, then add the body to the tree.
  - Packed arrays in a Dictionary: take a local, append, write it back.
  - Cache plans per blueprint and warm them at load.

## 8. Next classes

Hatchback, van, pod, bus, aerostat gondola. Each gets its own standard (frame ring, slots, shells,
tolerances) and a builder that follows section 4. The tests are generic: point them at the blueprints.
