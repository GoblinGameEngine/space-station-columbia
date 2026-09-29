# The Studio Ghibli look, and what it means for a 3D NPC generator

This file covers what makes a Ghibli character read as Ghibli, and how each trait carries into a
cel-shaded, real-time 3D character that is generated rather than hand-drawn. Sources are in
`ghibli_scholarship.md`, and the local reference material (stills, trailer frames, key-animation
clips, papers) is catalogued in `ghibli_references.md`. The numbers under **Measured** come
from `tools/charref/palette.py` run over the 1,200 official stills; they are not guesses.

---

## 1. The design principles

### 1.1 Characters are people with jobs, not costumes
Ghibli's background casts are working people: bakers, dock hands, bathhouse staff, farm wives,
engineers, schoolchildren, grandmothers, policemen. Scholarship calls this "constructed
realism" and "the spectacular mundane" (Crombie 2021; Law 2022 on the imagery of labour). The
films linger on work: cooking, scrubbing floors, stoking boilers, carrying loads.
A character's clothes, posture and props say what they do before they speak.

**For the generator:** occupation is the root trait. It drives the clothing slots (apron, work
trousers, uniform), the props (basket, tool bag, bicycle) and the idle actions (sweeping,
smoking at a doorway, hanging laundry), and it constrains palette and wear. This is the same
chain Watch Dogs Legion's Census uses (occupation → income → housing → clothing); see
`procedural_npcs.md`.

### 1.2 Uniforms, and individuality in hair, face and small things
In Spirited Away's bathhouse (chihiro 018, 026, 028) every young woman wears the same pink
work suikan and every frog-man the same outfit. Kiki's town has its police, postmen and
bakers. The individuality sits in hair shape, eyebrows, face shape, how they stand, and one or
two accessories. Crowd scenes (majo 045, 049; chihiro 033) are many simple people with varied
hair and a limited colour set, never a rainbow.

**For the generator:** role clothing comes from a small set of templates, and variation
comes from (a) hair shape, (b) facial proportions, (c) one or two accessories, (d) wear and
fading, and (e) a colour pick within the role's palette. This is the opposite of the random
outfit a sandbox RPG produces, and it is the main guard against "procedural soup".

### 1.3 The caricature axis
Protagonists and ordinary adults are drawn with restraint: small noses, modest eyes, few
lines. Elders, bosses, comic and villainous characters are pushed hard: Yubaba's huge head
(chihiro 016–017), Dola and her sons, the Laputa pirates, Porco's Mamma Aiuto gang, the
grandmothers. How far a face departs from the norm is itself a characterising choice.

**For the generator:** a `caricature` trait (0–1) scales how far the face morphs (head-to-body
ratio, nose size, jaw, brow, eye size and spacing) move from the population mean. Most NPCs
sit at 0.1–0.3; a few (market loudmouths, eccentric elders) get 0.6–0.9. It is chosen per
person and biased by age and personality. It is not uniform noise.

### 1.4 Solid bodies, real weight
Ghibli characters are grounded: they sag when tired, strain when lifting, lean into wind.
Kondo's "understated solidity", Takahata's insistence on real anatomy and muscle movement
(Only Yesterday prescored the dialogue so the faces could act to it), and Miyazaki's running
studies (the character's weight on the foot, the body leading) are the core of the look. Body
types vary widely and none are idealised: stout fathers (chihiro 004), heavy grandmothers,
lean boys, pregnant Osono (majo).

**For the generator:** a wide, honest spread of body types (§4 of `npc_traits.md`), with
posture and gait parameters tied to age, weight and personality.

### 1.5 Simple faces, emotional range
The standard Ghibli face is a slightly rounded oval with a small chin, a small nose often
drawn as a single line or two dots, eyes set wide and mid-face that are large but not
exaggerated, eyebrows that do most of the acting, and blush as a hatched patch. The mouth is a
line, or opens into a large simple shape. Pupils are dark with one or two highlights. Faces
change shape a great deal in expression (squash on laughter: majo 008, 013) rather than adding
detail.

**For the generator:** faces are drawn in the shader (eyes, brows, mouth and blush as
textures or SDF decals on a simple head mesh). They get expression through a small set of
blend shapes and brow and mouth shapes, not detailed geometry. Detail lives in the silhouette
(hair, head shape), not in the surface.

### 1.6 Hair as solid shapes
Hair is drawn as a few big clumps with a strong silhouette, two tones, sometimes one
highlight band, and flat dark outlines. It moves in wind as whole clumps (Haku, Sophie,
Nausicaä).

**For the generator:** hair is built from clump primitives (card strips, or a small set of
sculpted parametric pieces: fringe, sides, back, tail or bun) grouped into styles, with 2 to 3
colour tones and a few bones per clump for sway. VRoid's hair-chunk system is the closest
existing model; see `character_creators.md`.

---

## 2. Colour

### 2.1 Yasuda's approach
Michiyo Yasuda coloured every Ghibli feature from Nausicaä to The Wind Rises, choosing
several hundred colours per film. Her principles (from interviews summarised by Animation
Obsessive):
- colours are **semi-natural**, faded, a little greyed, chosen to sit in the background art
  rather than pop out of it;
- each character has day, evening, night and interior variants of their palette, not one
  palette darkened;
- **shadow is a colour**, not black: it is chosen per surface and tinted by the scene's light;
- colours follow period, material and dye (1950s rural Japan cotton vs. a 1990s Italian
  seaplane pilot).

### 2.2 Measured: the stills (tools/charref/palette.py)
HSV over every pixel, whole frames (characters and backgrounds together):

| film | median sat | median value | pixels with sat > 0.7 |
|---|---|---|---|
| Totoro | 0.32 | 0.41 | 4.6% |
| Kiki | 0.32 | 0.39 | 13.2% |
| Spirited Away | 0.31 | 0.51 | 3.5% |
| Only Yesterday | 0.26 | 0.63 | 9.1% |
| Poppy Hill | 0.26 | 0.47 | 0.6% |
| Arrietty | 0.29 | 0.38 | 0.6% |
| Porco Rosso | 0.34 | 0.51 | 22.2% (sea and sky) |
| Kaguya / Yamadas | 0.07–0.08 | 0.81–0.93 | ~0% (watercolour on white paper) |

- Across the cel films the median saturation is **about 0.25–0.35**. Strongly saturated
  pixels are rare, and when present they are mostly sky, sea or a single accent (Kiki's red
  bow, Porco's red plane).
- **The darks are coloured.** The darkest k-means clusters are blue-green, not neutral:
  Kiki #142028 / #1d283e, Totoro #161e20 / #293431, Porco #111f1c. There is almost no true black.
- **The lights are warm cream**, not white: #d1c2ae, #c8bda5, #d6cebe, #d1ceb9.
- The mid-tones are warm greys and browns (#836e62, #ab9074, #876a4b): wood, earth, skin,
  worn cloth.

**Rules for the generator (from this):**
1. Garment base colours are drawn from palettes with saturation mostly at 0.15–0.45 and value
   at 0.3–0.8. A character may have **one** accent (sat 0.5–0.8): a bow, scarf, bag or a
   child's shirt.
2. The shade colour for every material is its own colour: a hue shift toward blue or violet,
   higher saturation, lower value. It is never a multiply by grey. Skin shade shifts
   warm (toward red-orange), as in Ghibli and in Guilty Gear Xrd's tint texture.
3. Outlines are a dark tint of the neighbouring colour or of the scene's shadow colour, never
   #000.
4. White is cream (#e8e0cc-ish), black is dark blue-green or brown.
5. Fabric fades: saturation × (1 − 0.4·wear), value lifted slightly, most on the shoulders
   and knees.

The per-film k-means palettes (16 clusters, with shares) are in `reference/ghibli/palette.json`
and the swatch strips in `reference/ghibli/palettes/`; they are data the palette generator can
load.

---

## 3. Shading and line

### 3.1 In the films
Two tones: a lit colour and a shadow colour with a hard edge, and occasionally a third
highlight tone on hair or on shiny materials. Shadow shapes are designed, not computed:
animators simplify them into clean shapes, and a shadow keeps a stable shape across frames
(Petrovic et al. 2000 describe the manual labour, and a tool that computes these shapes from
a rough 3D model). Line is a thin, even, dark coloured line with little thickness variation;
colour-trace lines (lines in a colour, not dark) mark shadow borders and soft edges such as
cheeks.

### 3.2 How 3D productions reproduce this (Motomura, Guilty Gear Xrd, GDC 2015)
- **Kill everything 3D:** no specular, no ambient occlusion, no realistic falloff. Keep the
  lighting a step function.
- **Control the shadow line by hand:** the vertex normals are edited so faces shade as flat,
  clean planes, and a per-vertex threshold offset (in vertex colour) pushes the shadow toward
  or away from an area (areas that should stay lit, or be dark like the inside of a collar).
- **The shade colour comes from a tint texture**, multiplied in, so each area gets its own
  shadow hue.
- **Per-character light vector:** a character's key light is chosen so the character reads,
  not taken from the scene.
- **Inverted-hull outlines** with the width in vertex colour; **inner lines** drawn as texture
  lines on axis-aligned UVs so they stay crisp.
- **Limited animation:** poses held on twos or threes, no interpolation between keys, hand-made
  imperfection per frame.

### 3.3 What our generator does
Everything is procedural, so the "hand-edited" parts become rules:
- **Normals:** the head uses a sphere-projected normal (the classic anime face trick: the
  normals are transferred from a sphere or ellipsoid round the head) so the face shades as one
  clean shape. The body uses smoothed normals from a proxy shape per body part.
- **Threshold map:** generated per garment template, not painted: darker in folds (from the
  template's fold lines), under collars and at the neck, the inner arms and the crotch; lighter
  at the forehead, nose bridge and shoulders.
- **Shade colour:** computed per material with the rule in §2.2.2. No tint textures are shipped.
- **Outlines:** inverted hull in the vertex shader, width by camera distance and vertex weight
  (thin at the fingers and hair tips). No outline past ~60 m; far characters are flat
  silhouettes.
- **Scene light:** Godot's directional light, with the terminator snapped and the shadow
  receiving quantised to the same two tones.
- **Animation:** option to hold poses on twos (12 fps) for close NPCs, as Arc System Works
  did. To test in-game before deciding: it reads as anime up close but may look like lag at a
  distance or while the player moves.

---

## 4. Motion

- **Walk and run:** Miyazaki's rule was observation over formula. The Animation Obsessive
  study of his running notes shows 4-frame (on ones), 6-frame (on twos) and 8-frame cycles for
  different characters and moods, with forward lean, arm swing and foot contact all varying by
  who is running. We need a walk and run with parameters (stride, cadence, bounce, lean, arm
  swing, how much the heel strikes) driven by age, weight, mood and personality, not one cycle
  for everyone.
- **Ma (間):** pauses. Characters stop, look, breathe, do nothing (Brooks 2022). Idle NPCs
  should have genuine still time and small idle actions, not constant fidgeting.
- **Work actions:** labour is animated with care (Kamaji's arms, Kiki scrubbing, the boiler
  room). A library of work idles per occupation matters more than combat animation for an NPC
  town.
- **Cloth and hair in wind:** big simple shapes moving together. Use a few bones per garment
  hem and hair clump driven by wind and velocity, not simulated cloth.

The key-animation clips in `reference/ghibli/sakuga/` (tagged character_acting, walk_cycle,
running and fabric) are the motion reference for these.

---

## 5. Proportions

The widely repeated "Ghibli characters are N heads tall" claims have no source we could
find. From the stills: children ~4.5–5.5 heads, teenagers ~5.5–6.5, adults ~6.5–7.5 (Porco,
the Kiki and Only Yesterday adults), slightly shorter than realistic (7.5–8), with larger heads,
hands and feet. Elders and comic figures get very large heads (the caricature axis, §1.3). These
are eyeball estimates from a small number of full-figure stills. Before the base mesh is
fixed they should be measured properly (hand-annotated head and height points on 30–50
full-figure frames); this is a listed follow-up in `README.md`.

---

## 6. What to avoid
- **Big-eyed "anime" faces:** Ghibli's eyes are moderate. Generic anime proportions are the
  most common way "Ghibli-style" 3D goes wrong.
- **Saturated, clean colours:** see §2; the data are unambiguous.
- **Uniform noise over every trait:** people need to be coherent (occupation → clothing,
  age → posture), not random.
- **Detail in the surface:** folds, pores, rim light, specular all break the look.
- **Everyone moving the same way:** motion parameters are part of the character.
