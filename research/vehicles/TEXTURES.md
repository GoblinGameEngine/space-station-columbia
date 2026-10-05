# Vehicle textures (2026-10-05)

The user: "make textures for the models ... preferable to use generic textures that can serve multiple purposes.
Research how people do that when making very large worlds like ours."

## How large worlds do it

- **Tileable materials and trim sheets.** A few tiling textures (and trim sheets: strips that tile one way) cover
  thousands of assets; memory and draw calls stay low because nothing is painted per asset. Recommended for open
  worlds. (Roblox, "Develop polished assets": https://create.roblox.com/docs/en-us/tutorials/curriculums/environmental-art/develop-polished-assets)
- **Layered materials.** A material is a grey tileable surface tinted by a colour, with masks for dirt and wear, chosen
  per part by a material ID (vertex colour or an ID map). BeamNG's vehicles: a base colour/palette over shared detail
  maps (https://documentation.beamng.com/modding/vehicle/vehicle-art/texturing/texture-setup/); vertex-colour ID masks
  (https://80.lv/articles/breakdown-vertex-color-to-id-masks-ue5-plugin).
- **Triplanar projection** for meshes without UVs: the texture projected along three axes, blended by the normal --
  consistent density on every object, no seams to hide (https://godotshaders.com/shader/triplanar-mapping/;
  https://80.lv/articles/ue5-triplanar-deep-dive-from-worldalignedtexture-to-high-quality-normals-part-1/). In
  *world* space a moving vehicle's texture would swim; in the object's own space it rides with it.
- **Decals / stickers** add the unique details (lettering, crosses, gauges, plates) over the shared surfaces.

## What the fleet does

- `tools/assets/surfaces.py` makes ten tileable 512 px surfaces (albedo grey, normal, roughness) from periodic noise:
  paint (orange peel), plastic (stipple), brushed metal, rubber (block tread), fabric (weave), canvas (coarse weave,
  stitched seams every metre: the envelopes' gores), wood (grain and rings), vinyl (pebbled leathercloth), carpet,
  bone (the Steward's printed alloy).
- The palette material's name is the material ID: `VehicleLibrary.SURFACE` maps each (paint, black, chrome, rubber,
  seat, carpet, lining, wood, canvas1/2 ...) to a surface and a tile size. The palette colour tints it, so every
  style and every livery shares the same few maps.
- StandardMaterial3D's own triplanar, in object space (`uv1_triplanar`, not world): no UVs needed, nothing in the
  pipeline changed, and it applies to all 136 types at once. Glass, lamps and screens stay untextured.

## Dirt and wear (2026-10-05)

- `remake/shaders/vehicle_surface.gdshader` replaces the standard material for every surfaced palette entry: the same
  tinted triplanar surface, plus road grime rising from the ground (ragged, splotched, with drips: `grime_mask.png`),
  dust on upward faces, and wear -- paint chipped to primer and bare metal along sharp convex edges.
- The edge mask is baked per vertex by `kit/components.py` (`edge_wear`: the angle across each convex edge) and written
  after the normals in each pack (catalog entries flag `"wear": true`); the game carries it as COLOR.r = 1 - wear.
  Only sharp edges chip: a low-poly panel's vertices nearly all sit on seams, and seam wear greyed whole panels.
- Each body gets its own `grime` and `wear` (instance uniforms, random per vehicle; `VehicleBody.weather(g, w)`).
- Cabin materials (seats, carpet, linings, dash) take no road dirt. Normal maps stay off (the outline speckles them).

## Decals (2026-10-05)

- `tools/assets/decals.py`: plates (eight Columbia plates, VY 500), the gauge cluster, the star of life, rear chevrons,
  white lettering (tinted per livery: FIRE DEPT, MARSHAL -- the station's police -- TAXI, AMBULANCE, POST, SCHOOL BUS ...)
  and fleet numbers -> godot_project/remake/vehicles/decals/.
- `remake/blender/fleet/decals.py` places them per type (LIVERIES): plates front and rear on road vehicles, gauges on the
  dash ahead of the wheel, lettering on the cargo body or below the windows, chevrons across heavy vehicles' rears,
  words on envelopes and hulls. The blueprint's "decals" carry them (Godot frame); the game projects each as a Decal
  riding with the body (fading out past 45 m), choosing one plate and one fleet number per vehicle.

## Next

- Trim sheets for the hand-built parts (grilles, vents, tread plate); lamp lenses with reflectors.
- Dirt by use (a farm truck dirtier, a hearse spotless): the callers can set `weather()` by type.
