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

## Next

- Decals with UVs (option 2 in the session's notes): liveries' lettering, the red cross, gauges, plates, lamp lenses.
- Dirt and wear masks (dirt by height above the ground, wear on edges) in a shader over the same maps.
- Trim sheets for the hand-built parts (grilles, vents, tread plate).
