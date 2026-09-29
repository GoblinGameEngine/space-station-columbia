# Generator design notes: from traits to a cel-shaded person on screen

This is the build plan that follows from the research. It covers the look in
`ghibli_style.md`, the parameters in `npc_traits.md` and the runtime model in
`procedural_npcs.md`. Nothing here is built yet. These notes are the starting point for
the build phase, after the literary research.

---

## 1. Pipeline

```
request (procedural_npcs.md 2.5)
  -> resolve id                       (implicit resident / transient)
  -> traits L0, L1                    (npc_traits.json, per-trait streams)
  -> body:   base mesh + shape keys   (height, build triangle, proportions, age, head, caricature)
  -> face:   head shape keys + face shader params (eyes, brows, mouth, blush, marks)
  -> hair:   clump set for the style + colour params + sway bones
  -> outfit: occasion -> slots -> garment templates + params + fabric params
  -> motion: gait params, idle set from occupation, hold-on-twos flag
  -> placed by schedule(t), shown; L2/L3 generated on contact
```

All meshes are **shared resources**. A person is a skeleton, a few `MeshInstance3D`s with
their blend-shape weights set, and a material parameter block. There are no per-person
textures or meshes.

## 2. Body
- **One stylised base mesh** per sex (or one with a sex blend), ~3–5k triangles, on one
  skeleton (humanoid, ~50 bones plus a few per hair clump and hem). Proportions come from
  `ghibli_style.md` §5, once measured.
- **Shape keys:** height is done by bone scale rather than a shape key. The build triangle
  (thin, muscular, heavy), leg length, shoulders, hips, head size, age (child, elder, the
  latter a pass that sags and stoops), pregnancy. Child bodies need proportion keys (big head,
  short limbs), not just scale.
- **Normals:** smoothed proxy normals per part (Motomura's "kill everything 3D"): the torso
  shades as a cylinder, the head as a sphere.
- Authoring: Blender, from our own base or MPFB's CC0 mesh restyled, exported to GLB with shape
  keys. A Blender script generates the shape keys from a few sculpted extremes.

## 3. Face
- A simple head mesh with face shape keys (width, jaw, chin, cheek, nose, eye spacing,
  mouth width), scaled by `caricature`.
- **Features drawn in the shader**, not modelled: the eyes (white, iris, pupil, one or two
  highlights, lid line), brows, mouth line and shapes, blush hatching, freckles, moles,
  wrinkles, stubble. Each is an SDF or small atlas shape placed in a head-space UV frame
  with per-person offsets and sizes. The atlas is small and shared: a few dozen shapes for eyes,
  brows and mouths, drawn once in Ghibli's restrained style.
- **Expression:** mouth and brow shape swaps plus a few blend shapes (squash on laughter,
  cheeks up). The shader parameters are animatable, so blinking and talking cost nothing.
- **Glasses, beards, moustaches:** small shared meshes, with the beard's shape from shape
  keys.

## 4. Hair
- Each style is a set of **clumps** (fringe, sides, back, tail, bun, braid) as low-poly
  sculpted shells with shape keys for length and volume, following the VRoid clump model.
  Around a dozen styles × 2–3 length variants covers the trait list.
- Two to three tones in the shader: base, shade, one highlight band (an anisotropic band
  quantised to a hard edge). Greying blends toward the grey ramp by `hair_grey`, streaked by a
  noise mask.
- **Sway:** 2–3 bones per clump, driven by a spring on head motion plus wind. No simulation.

## 5. Clothing: procedural, no texture catalogue

### 5.1 Garment templates
There are about 30–40 low-poly templates, authored on the base body **with the same body
shape keys**, so they fit any build (the Sims and MPFB approach; add Roblox-style cages only
if needed):

- tops: T-shirt, collared shirt, blouse, polo, sweater, cardigan, vest, apron (bib, waist),
  overalls bib, school sailor top, kimono or happi-style jacket for festivals;
- outer: work jacket, blazer, raincoat or oilskin, winter coat, shawl;
- bottoms: trousers (straight, work, rolled), shorts, skirt (straight, A-line, pleated),
  dress (shift, pinafore, work dress);
- head: cap, flat cap, brimmed hat, straw hat, headscarf, hairband, hard hat;
- feet: shoes, boots, sandals, rubber boots;
- carried or props: basket, satchel, shopping bag, tool bag, bicycle.

Each template has parameters as garment shape keys (length, looseness, sleeve length,
rolled cuffs, collar type), and **fold lines**: a baked mask used by the shader for the
shade-threshold offset (`ghibli_style.md` §3.3).

### 5.2 Fabric in the shader
One uber-shader with a parameter block per garment:
- `pattern`: solid, stripes, pinstripe, check / gingham, plaid / tartan (thread counts),
  polka dot, small floral stamp, herringbone hint, knit rib, denim twill;
- `colours[4]`, `scale`, `angle`;
- `wear`: fading (saturation × (1 − 0.4·wear)), lighter at the shoulders, knees and elbows,
  plus patches (a stamped rectangle of another fabric) above 0.7;
- `dirt`: hem and knee darkening, for farm and dock workers;
- the shade colour is computed per material (hue toward blue-violet, saturation up, value
  down; skin shifts warm), as `ghibli_style.md` §2.2.

Patterns are evaluated in garment UV space, which is laid out per template so stripes run
the right way.

### 5.3 Outfits and changing clothes on the fly
- An **outfit** is data: `{slot: {template, params, fabric}}`, generated from
  `occupation.outfit` + `style` + `palette` + `accent` + `wear` + the weather.
- Each person has an **outfit set**: `work`, `casual`, `formal`, `sleep`, and weather
  overlays (a raincoat over anything; a winter coat, scarf and hat when cold). The same seed
  gives the same wardrobe, so she wears *her* raincoat, not a random one.
- **Changing** swaps MeshInstances on the skeleton and updates the material parameters.
  It takes a frame or two and can happen at any time (going home, rain starting, a quest giving
  a uniform). A delta can record a new or given garment.
- **Layering:** slots are ordered (body → shirt → sweater → jacket → coat). Body regions
  hidden by an outer garment are masked (the Sims approach: each template declares the body
  regions it covers, and the body and inner garments discard those triangles via a
  vertex-colour region ID) to prevent clipping.

### 5.4 Costume rules (curation against soup)
- **Occupation decides the silhouette**, and personal choice decides the colour and
  accessories: the bathhouse rule (`ghibli_style.md` §1.2). Uniformed jobs (police, postal,
  nurse, school) use fixed colours; only accessories vary.
- **One accent per person**, most often on a child. Base colours come from the palette
  family with saturation ≤ 0.45.
- **Pattern budget:** at most one patterned garment per outfit, with larger patterns on
  bigger garments. Children and the flamboyant style may have two.
- **Age and period:** elders dress older (cardigans, hats, headscarves); the young wear
  sporty and plain things.
- **Income** sets the fabric quality and wear, not the garment choice.
- **Weather** overlays follow the station's climate bands.

## 6. Shading and line
- A Godot `ShaderMaterial` with **two-tone quantised lighting** (lit/shade with a hard,
  slightly softened step), the threshold offset from the fold mask and vertex colour, and the
  shade colour per material.
- **Outline:** an inverted-hull second pass, with width in vertex colour and scaled by view
  distance, coloured as a dark tint of the base (never black), faded out past ~60 m.
- **Rim or specular:** none, except a hair band and the eye highlights.
- **Receiving shadows:** quantised to the same two tones.
- It must match the existing world shading. Check against the current terrain and building
  cel look before committing.

## 7. Animation
- One shared set of locomotion clips (walk, run, stop, turn) retargeted to the skeleton and
  **modulated** by gait params (stride, cadence, bounce, lean, arm swing) with blend-space
  and additive layers.
- **Idle and work libraries** keyed by occupation (sweeping, carrying, kneading, fishing
  line, sitting, reading, smoking at a doorway, chatting pairs). Ma: long idles with real
  stillness.
- An optional **hold on twos** for near NPCs (animation sampled at 12 fps), to test.

## 8. Performance targets (Steam Deck)
- 40–80 full NPCs near the player; beyond ~80 m, impostors (a pre-rendered or flat
  silhouette sprite from a few angles, generated on first need and cached per person for the
  session).
- L1 derivation < 0.5 ms; assembly spread over frames from a pool, with no allocation in
  steady state.
- One draw call per mesh part, with no texture sampling beyond the shared face and stamp
  atlases.

## 9. Tools to build (to make the job easier)
Already built (tools/charref/):
- `contact_sheets.py`: reference sheets per film;
- `palette.py`: measured colour statistics and palettes;
- `sakuga.py`: resumable motion-reference fetch;
- `traits.py`: validate the trait file, preview people, distribution stats, determinism.

To build with the generator:
1. **Lineup scene** (`remake/tools/npc_lineup.tscn`): a row of 20 generated people on a
   turntable under standard light, reached from DevBridge. Args: seed, request filter,
   occasion. The main visual check. Screenshot to compare with the reference sheets.
2. **Crowd scene:** 200 people in a street, to judge soup, twins and palette as a whole
   against a Ghibli crowd still.
3. **Single-person inspector:** every trait with its value and source (the stream, the
   mods applied), live-editable, with "reroll this trait" and "explain" (like
   `RoadScan.explain`).
4. **DevBridge commands:** `npc.request({...})`, `npc.explain(id)`, `npc.dress(id, occasion)`,
   `npc.where(id, t)`.
5. **Parity test:** the Python tool vs. the GDScript generator on a few hundred ids. They
   must match exactly.
6. **Blender scripts:** base mesh shape-key generation, garment template export (with
   fold mask and region IDs), and hair clump export.
7. **Proportion annotator:** click the head top, chin and feet on reference stills and store
   ratios, for measuring `ghibli_style.md` §5 properly.
