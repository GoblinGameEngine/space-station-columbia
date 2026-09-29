# Tens of thousands of NPCs we never track: lazy, deterministic generation

The requirements, in the user's words:
- a procedural generator that "will run from a prompt the game creates";
- real time: "new characters are created and added to a game state on the fly as needed";
- "put the character where they need to be on the fly without having to run through its
  entire routine while it is not directly needed by the player";
- "seamless and done only on initiation of contact, so that we can have tens of thousands of
  procedurally generated characters that we do not have to track".

This file sets out the research basis and the architecture that follows from it. The trait
schema is in `npc_traits.md`; the look (meshes, clothing, shading) is in
`generator_design_notes.md`.

---

## 1. What the research says

| idea | source | what it gives us |
|---|---|---|
| **Uprezzing on demand** | Watch Dogs Legion Census (GDC 2021) | NPCs start shallow; deeper layers are generated only when the player looks closer, consistent with what was already seen |
| **Alibi generation** | Sunshine-Hill & Badler 2010 (`reference/papers/`) | an unobserved NPC isn't simulated; when first observed, the system generates a past (where they were, what they did) consistent with the present |
| **AI level of detail** | Brom et al.; Game AI Pro 1 ch. 43 | simulation detail falls off with distance and relevance, down to none |
| **Story-consistent retroactive facts** | Riedl et al. (`reference/papers/`) | facts are committed only when observed, so the unobserved world stays flexible |
| **Knowledge and beliefs** | Talk of the Town (Game AI Pro 3 ch. 37) | what NPCs know about each other; later phase |
| **Believability over realism** | Bates 1994 | spend the budget on what the player perceives |

All of these amount to one principle: **a character is a function, not a record.** The
world stores seeds and a few rules. A character is computed from them when needed, and the
same inputs always give the same person. Only what the player **changes** is stored.

---

## 2. The architecture

### 2.1 Identity: every possible person has an address
There are two populations, both implicit:

1. **Residents.** Every residential building on the map is already known (the map and the
   building catalogue). A household is a pure function of `(world_seed, building_id)`:
   its size, the members' ages and relationships, and income (from the town's demographic
   archetype; see `research/demographics/_demographic_archetypes.md`). A person's id is
   `building_id:member_index`, for example `B14823:2`. Tens of thousands of residents exist this
   way at zero storage cost.
2. **Transients.** Visitors, travellers, delivery drivers and anonymous passers-by: a pure
   function of `(world_seed, place_cell, day, slot)`. Their id is `T:<cell>:<day>:<slot>`. They
   exist for a day.

Workplaces pull from residents: a shop's staff are residents whose derived occupation is
that shop's trade, found by a deterministic search of nearby households (cached once per
town, as a small table).

### 2.2 Layers, generated lazily
Each person has layers, each a pure function of `(person_id, layer)` plus anything the layer
depends on:

| layer | contents | generated when | cost |
|---|---|---|---|
| **L0 core** | sex, age, occupation, household role, income band | on any query (a list of who lives here, who works there) | microseconds; no allocation |
| **L1 appearance** | body, face, hair, skin, outfit set, palette, gait | when the person is about to appear on screen (spawn radius) | ~0.1–0.5 ms to derive; the mesh assembled over a few frames |
| **L2 persona** | name, personality facets, speech style, preferences, a short backstory | on **contact**: the player looks at them, talks, or targets them | ~ms; optional Groq call for flavour text, which is cached |
| **L3 life** | schedule, relationships (by id), history, secrets, knowledge | on deeper contact: quests, investigation, a return visit | ~ms |
| **Δ delta** | anything the player caused: an injury, a gift, a changed opinion, a new job, killed, moved | when it happens | **the only thing saved** |

**Rule:** a layer may depend on lower layers and on the world, never on higher ones. That
keeps L1 (what you saw across the street) from contradicting L2 (what you learn when you
talk), because L2 is derived *from* L1 (a fisherman's clothes come from his L0 occupation, and
his backstory then takes the occupation as given).

### 2.3 Determinism that survives adding traits
The user wants to add characteristics over time. If all traits came from one random stream,
adding a trait would shift every value after it and change every existing character. So:

- **Every trait has its own stream:** `rng = hash(world_seed, person_id, trait_name)`.
  Adding a new trait adds a new stream and changes nothing else.
- Changing a trait's **distribution** changes only that trait (and the traits that depend on
  it, by design).
- Trait definitions carry a `version`. Saved deltas record trait values explicitly, so a
  person the player knows stays the same even if a later update re-tunes the distribution.
- Hash: a 64-bit string hash (e.g. xxhash64 or FNV-1a over `"seed|id|trait"`), turned into a
  PCG stream. The same algorithm is used in GDScript and in the Python tools, so tools can
  preview the exact person the game will make.

### 2.4 Placement without simulation (the "alibi" approach)
The user's requirement: put the character where they need to be without running their
routine. So the **schedule is a pure function of time**:

`where(person, t) -> (place_id, activity, since, until)`

It is computed from L0 and L3: occupation hours, the household's routines, and day-of-week
and weather modifiers, with the person's own stream adding jitter ("leaves work 17:05–17:40").
Nothing is simulated in between. When the game needs to know (the player enters the bakery at
08:10, or asks "where is Marta?"), it evaluates the function **then**. If the player sees the
person, the answer becomes a fact; if the player changes something (asks her to meet at the
pier at 18:00), the change is a **delta** that overrides the function for that span.

The same function answers population queries in reverse: "who could plausibly be in this
street right now?" is a cheap sample over nearby households' L0 plus the schedule function,
used by the spawner to populate a street with people who **live there**, so a player who
follows one home finds the house they belong to.

### 2.5 The "prompt": a request the game makes
"Run from a prompt the game creates" means a structured **character request**, not natural
language. It is the one entry point every system uses (the ambient spawner, quests, dialogue,
the director). The generator either finds an existing implicit person who fits or, if none fits
(or the request allows it), mints a transient.

```json
{
  "where":   {"place": "bakery:B2201", "or_near": [12840.5, -310.0], "radius": 40},
  "when":    "now",
  "want":    {"occupation": "baker", "age": [30, 60], "role": "shopkeeper"},
  "prefer":  {"personality": {"warmth": [0.6, 1.0]}},
  "must":    {"not": ["already_met"]},
  "reason":  "ambient|quest:lost_cat|dialogue_ref",
  "depth":   "L1|L2|L3",
  "persist": false
}
```

The steps:
1. **Resolve:** search the implicit population (the households near `where`, whose L0 fits
   `want` and whose schedule puts them there at `when`). The search is deterministic and bounded
   (it checks at most N households in order of distance). Otherwise it mints a transient whose
   seed is the request's hash, so repeating the request gives the same person.
2. **Generate** up to the requested depth.
3. **Place:** spawn at `where` and choose a spot and action from the activity (behind the
   counter, kneading), not by walking there.
4. **Persist** only if `persist` is true (a quest giver) or when a delta happens.

### 2.6 Budget on the Steam Deck
- **On screen:** a pool of perhaps 40–80 live NPCs near the player at full detail, and
  impostors or flat silhouettes beyond ~80 m. Hundreds would be too many for the Deck with
  outlines.
- **L1 assembly:** the body mesh is shared (shape keys set per instance), and garments are
  shared meshes (shape keys per instance). There is **no per-NPC texture:** faces and fabrics
  are shader parameters. So a new character costs a few mesh instances, a skeleton and a
  material parameter block, which is cheap enough to do while walking up to someone.
- **Spawn ahead:** the spawner generates L1 at ~120 m and shows it from ~80 m, so the pop-in
  is hidden by distance and the outline fade.
- **Recycling:** a pooled NPC scene is re-dressed for the next person rather than freed.
- **Saves:** deltas only. A heavily played save might record a few thousand people's deltas,
  which is kilobytes.

### 2.7 What is stored
- World: `world_seed`, and the trait definitions (data files, shipped with the game).
- Per town: a small cache table (workplace → staff ids) computed at load or bake time.
- Per person the player affected: `{id, trait overrides, schedule overrides, flags,
  relationship changes, knowledge}`.
- Nothing else. A person the player walked past once and never affected is regenerated
  identically next time, and was never saved.

---

## 3. Failure modes to design against

- **Contradiction:** L2 or L3 contradicting what the player saw. Prevented by the layer rule
  and by deriving from L1.
- **Procedural soup:** valid but meaningless combinations (Census). Prevented by occupation →
  outfit chains, curated palettes and trait exclusions (`npc_traits.md` §3).
- **Twins in a crowd:** two identical-looking people on screen. The spawner checks L1 hashes
  of the live pool and skips near-duplicates; the face gene space must be big enough.
- **"Everyone is home at noon":** schedules must be plausible for the archetype (workers
  away by day, retirees in town, children in school), or streets feel wrong.
- **Pop-in:** hide with spawn distance and fades; never spawn in view within 40 m.
- **Save bloat:** only deltas; prune deltas of transients who left the world.
