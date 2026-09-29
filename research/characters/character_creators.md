# How games build characters: creators, NPC generators and clothing systems

This is a survey of how first-person, open-world and systemic RPGs (and a few tools) build
characters, both the player's character creator and the NPC pipeline behind it. Each entry
ends with **Take:** what we borrow. Where there are links, they are the primary sources used.

---

## 1. Player character creators (the parameter spaces)

### Bethesda: Oblivion → Skyrim → Fallout 4 → Starfield
- **Oblivion (2006):** FaceGen. Faces are a statistical space (principal components from
  scanned heads) with sliders for age, "race" and each feature. Randomise produces plausible
  but same-ish faces.
- **Skyrim:** preset heads per race, plus sliders and tint layers (war paint, dirt,
  complexion) composited into the face texture.
- **Fallout 4:** "sculpt" by dragging regions of the face directly. The **body triangle**
  (thin, muscular, heavy): a single point in a triangle blends three body targets. It is simple,
  readable and covers most builds with two numbers.
- **Starfield:** the triangle again, plus a large preset library, with a "walk style" chosen
  in the creator. Motion is part of identity.
- **Take:** the body triangle as the UI and data model for build (two barycentric numbers),
  separate from height. Walk style as a creator parameter.

### Crusader Kings III (DNA genes)
CK3 characters are stored as a DNA string of genes (dev diary #34; ck3 wiki
"Characters_modding"):
- **Morph genes:** a pair of templates (e.g. `nose_size`: small/large) and a value that blends
  between them.
- **Accessory genes:** a pick from a list (beards, hairstyles, clothing).
- **Colour genes:** a 2D coordinate into a colour-map texture (skin, hair and eye colour). A
  point in a gradient image is much better than RGB: every point is a plausible colour.
- **Ethnicities** are templates of gene distributions; children **inherit** from parents
  (per-gene blend or pick, with mutation).
- Clothing is chosen by rules from culture, rank and era, not stored in the DNA.
- **Take:** our trait model is essentially this: typed genes (morph, pick, colour) drawn from
  population templates, with inheritance for families. Colour genes as 2D palette coordinates
  are adopted directly. Clothing by rule from role and culture.

### Mount & Blade II: Bannerlord (BodyProperties)
A character is a 64-bit-ish key encoding face and body values, plus age, weight and build.
Each culture and occupation defines a **min and max BodyProperties template**, and NPCs are
generated uniformly between the two. Hairstyles and beards are keyed by culture.
- **Take:** the whole face as a compact key. Range templates per population and role are an
  easy way to make "fishermen look weathered" and "clerks look soft".

### MakeHuman / MPFB (Blender)
An open, CC0 base mesh with **macro** modifiers (gender, age, muscle, weight, height,
proportions, African/Asian/Caucasian blend) plus hundreds of targeted modifiers. Each modifier
has a neutral value, a maximum deviation, and discrete or continuous type; macros drive
combinations of targets. It has a standard skeleton and proxies for clothes fitted to the body.
- **Take:** the macro plus target structure, with modifiers declared in data (name, neutral,
  deviation, type). This is what the user asked for: characteristics can be added without
  code. The CC0 base mesh is a possible starting point, but we will likely build a stylised base
  mesh (Ghibli proportions, §5 of `ghibli_style.md`).

### VRoid Studio
An anime character creator with face sliders, material pickers and a **hair editor** in which
hair is built from guided strands grouped into clumps, rendered as cards with toon materials.
Exports VRM (glTF with MToon shading).
- **Take:** hair as parametric clumps. The MToon material (shade colour, shade shift,
  outline width) is a well-documented toon parameter set to copy.

### Others worth noting
- **Cyberpunk 2077:** body type and voice decoupled from gender presentation. A preset face
  per part (nose 1–21) rather than continuous sliders. **Take:** discrete indexed parts are
  cheap to store and easy to curate.
- **Black Desert:** extreme slider depth. **Take:** a warning. Players can use depth,
  generators cannot; more sliders make procedural output worse unless curated.
- **The Sims:** personality traits and aspirations drive behaviour; clothing by occasion
  (everyday, formal, sleep, swim, athletic, party). **Take:** outfits per occasion, switched at
  runtime (the user's "change clothing on the fly").
- **Dragon's Dogma / Elden Ring:** sliders plus a "musculature" and "age" pass, and a face
  "detail" layer. **Take:** age as a pass over everything (skin, posture, hair colour, gait).

---

## 2. NPC generators in shipped games

### Watch Dogs: Legion "Census" (Ubisoft Toronto, GDC 2021; gamedeveloper.com write-ups)
The closest match to what we are building: every NPC in London is recruitable, so each has
a generated life.
- NPCs start **shallow**. When the player looks closer (profiling them, or interacting), they
  are **uprezzed**: deeper layers (family, schedule, relationships, backstory, skills) are
  generated on demand, consistent with what the player has already seen.
- The generation is a chain: **occupation → income → housing → schedule → clothing**, each
  probabilistic given the previous one.
- Three **simulation tiers:** fully simulated near the player; a coarse schedule in the
  middle distance; not simulated at all beyond that, only regenerated consistently when needed.
- The team's stated main risk was **"procedural soup"**: combinations that are technically
  valid but mean nothing. Curation of the chains and the rules was most of the work.
- **Take:** nearly everything. Lazy uprezzing on contact is exactly the user's requirement.

### RimWorld (Ludeon)
A pawn gets a childhood and an adulthood **backstory** from curated lists. Each backstory
sets skills, disables some work types, fixes the body type, and can force traits. Traits are
chosen from a list with exclusions (e.g. not both "kind" and "psychopath").
- **Take:** backstory as a bundle of consequences (not just text). Exclusion and requirement
  rules between traits.

### Dwarf Fortress
Each creature has 50-odd personality facets (0–100), values and beliefs, dreams, and
preferences (likes a material, a colour, an animal...). The distributions are tiered (most
people near the middle, few extreme), and personality shows in thoughts and conflicts.
- **Take:** facets as numbers with a mid-weighted distribution. **Preferences** (a favourite
  colour, food, place) are cheap and give NPCs specific things to say, and they can feed the
  clothing colour pick.

### Shadows of Doubt (ColePowered)
A procedural city where every citizen has a home, job, schedule, relationships and
**physical details the player can use as clues:** fingerprints, height, shoe size, hair,
handwriting, blood type. Citizens are simulated at low detail when unseen.
- **Take:** physical traits that matter in play (detective-style descriptions: "a tall woman
  with a red scarf who works at the bakery") must be consistent and derivable.

### Oblivion "Radiant AI"
NPCs run schedules from **packages** (eat, sleep, work, wander at a place and time). The
original, fully simulated version produced absurd emergent behaviour and was cut back.
- **Take:** schedules as data packages. Don't simulate unseen NPCs in full.

### Talk of the Town (Ryan, Mateas et al.; Game AI Pro 3 ch. 37)
A town of 300–500 simulated characters over 140 years, with 24 heritable facial attributes
and **knowledge propagation:** characters hold beliefs about each other, which can be wrong,
decay and spread by talk.
- **Take:** facial attributes heritable in families, and describable in words (the game knows
  "she has her mother's nose"). Knowledge is a later-phase idea, but it depends on the
  appearance schema being describable.

### Versu / Praxis, Comme il Faut / Prom Week
Social simulation with **social practices** (a dinner party, a greeting) that define roles
and what a character in that role can do. Characters have traits and relationships that weight
the options.
- **Take:** later, for the dialogue and literary phase. Our trait schema must leave room
  for relationship and social-norm data.

### Believable agents: Bates 1994, and AI level of detail
Bates (Oz project) argued that **believability** (the appearance of emotion and intention)
matters more than realism. Brom et al. (AI LOD) and Sunshine-Hill & Badler 2010 (**alibi
generation**) argue that unseen characters need not be simulated. When the player first
scrutinises one, the system **retroactively generates** a plausible account of what the
character was doing, consistent with anything already observed.
- **Take:** the principle behind "tens of thousands of NPCs we don't track". See
  `procedural_npcs.md`.

---

## 3. Clothing systems

| system | how garments fit | how outfits change | take |
|---|---|---|---|
| **GTA V** | fixed body per ped model | 12 component slots (head, torso, legs, feet, hands, accessories...), each a drawable + texture + palette index | slots with index + palette, cheap to store and swap |
| **The Sims 4** | garments authored to one base body + body morphs applied to garments | outfits per occasion (everyday, formal, sleep...) swapped instantly | occasion outfits |
| **Roblox layered clothing** | each garment has an **inner and outer cage**; a wrap deformer fits the garment to any body cage | layered, any order, at runtime | the cage idea: garments fit any generated body |
| **MakeHuman / MPFB proxies** | garments carry offsets to the base mesh and follow its modifiers | swap proxies | same idea, simpler |
| **GarmentCode** (Korosteleva & Sorkine-Hornung, SIGGRAPH Asia 2023, MIT licence) | parametric **sewing patterns** in code (panels, stitches, parameters like sleeve length, skirt flare), draped by simulation | new garments generated from parameters | a parametric garment grammar; we use it offline or as design reference rather than simulate at runtime |
| **Procedural fabric shaders** | n/a | pattern generated on the GPU from parameters (tartan thread counts, stripe widths, dots, checks) | no texture catalogue, as the user asked |

**Our approach (details in `generator_design_notes.md`):**
- A shared skeleton, and body **shape keys** from the traits (the body triangle, height,
  proportions, age).
- A few dozen **garment templates** (shirt, blouse, sweater, jacket, coat, trousers, skirt,
  dress, apron, overalls, uniform tunic, hat types, footwear), each a low-poly mesh authored on
  the base body **with the same shape keys**, so it deforms with the body (the Sims / MPFB
  approach; Roblox cages if needed).
- Each template has parameters (length, fit/looseness, sleeve length, collar type), done as
  shape keys on the garment, and a **fabric**: a pattern type, 2–4 colours, scale, wear.
  Evaluated in the shader, so no textures are shipped.
- An outfit is data: `{slot: (template, params, fabric)}`. Changing clothes swaps
  meshes on the skeleton and changes shader parameters, which takes a frame. Layering order
  comes from the slots (underwear/body → shirt → sweater → jacket → coat), and inner layers
  hidden by outer ones are culled by a mask, not simulated.
