# Character generator research: Ghibli-style NPCs

Research for the procedural NPC generator: Ghibli-style characters, generated on contact,
tens of thousands of them untracked, with body type, size, weight, face and clothing defined
by data, and clothes changeable at any time. The phases are: **this research** → literary
research (names, backstories, speech, preferences) → the generator build.

| file | contents |
|---|---|
| [ghibli_style.md](ghibli_style.md) | what makes the look (design, colour with measured data, shading and line, motion, proportions) and how each part carries into real-time 3D |
| [character_creators.md](character_creators.md) | how games build characters: Bethesda, CK3 DNA, Bannerlord, MPFB, VRoid, Census, RimWorld, Dwarf Fortress, Shadows of Doubt, Talk of the Town; clothing systems |
| [procedural_npcs.md](procedural_npcs.md) | the runtime model: a character is a function of (seed, id); lazy layers; placement by schedule function; the character request ("prompt"); what is saved |
| [npc_traits.md](npc_traits.md) + [npc_traits.json](../../godot_project/remake/characters/npc_traits.json) | which characteristics a rich cast needs and why; the **extensible data schema** (add a trait by adding an entry) |
| [generator_design_notes.md](generator_design_notes.md) | the build plan: body, face, hair, procedural clothing and fabric, outfits per occasion, costume rules, shading, animation, budget, tools |
| [scale_survey.md](scale_survey.md) | **characters at scale**: Watch Dogs Legion (9M), Ultima Ratio Regum (10M), Dwarf Fortress, Cities: Skylines, AC Unity, population synthesis, crowd-perception studies, never-fail body and face spaces; where our design goes beyond them |
| [ghibli_scholarship.md](ghibli_scholarship.md) | bibliography, annotated, with read and listed status |
| [ghibli_references.md](ghibli_references.md) | the local reference library (stills, trailers, key frames, key-animation clips, papers) and how to rebuild it |

## Conclusions
1. **No LLM is needed to generate characters.** A deterministic function of
   (world seed, person id, trait) makes the same person every time. Only what the player
   changes is saved. An LLM (Groq) is optional, for flavour dialogue, and is cached.
2. **Occupation is the root trait.** Ghibli's casts are working people, and Census makes the
   same chain (occupation → income → clothing). Clothing silhouette comes from the job;
   individuality comes from hair, face, one accent and wear.
3. **The colours are measured, not guessed.** Median saturation is about 0.3; darks are
   blue-green, never black; lights are warm cream; at most one saturated accent per person.
4. **Clothing is procedural:** ~30–40 garment templates sharing the body's shape keys, with
   fabric patterns evaluated in the shader from parameters. There is no texture catalogue.
   Outfits are data, so changing clothes is instant.
5. **Characteristics are data** (`npc_traits.json`). Each trait has its own random stream, so
   adding one never changes existing people (verified: 2,000/2,000 unchanged).
6. **The main risk is "procedural soup".** It is prevented by chained rules, curated palettes
   and templates, and by checking distributions (`traits.py --stats`) rather than
   individuals.

## Tools (tools/charref/)
- `traits.py`: validate `npc_traits.json`, preview people (`--id`, `-n`), distributions
  (`--stats`).
- `palette.py`: colour statistics and palettes from the stills.
- `contact_sheets.py`: numbered reference sheets per film.
- `sakuga.py`: resumable key-animation clip fetch.
- `measure.py`: proportions on stills (`data/proportions.csv`).
- `shade_pairs.py`: lit vs shade paint pairs (`data/shade_pairs.csv`).

## Open follow-ups
- ~~Proportions~~: measured (13 figures), adults ~6.25 heads, teens ~5.2. More figures would
  tighten it.
- ~~Character colour~~: lit and shade pairs measured (29), and the shade rule is in `ghibli_style.md` §2.3.
- ~~Town archetypes~~: `populations` in `npc_traits.json`. Next: household-first synthesis
  (`scale_survey.md` §2.4).
- Psychological and interpersonal research (next, after the generator): personality, ties,
  responsibilities, a place in the story; then the literary phase: name lists, backstory bundles, preferences, speech and dialect.
- Build: the lineup and crowd scenes first, then the base mesh, garments and shader.
