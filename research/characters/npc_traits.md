# NPC characteristics: what a rich cast needs, and the extensible schema

The characteristics live in **`godot_project/remake/characters/npc_traits.json`**, a data file the game loads. To add one, add an entry;
no code changes. Check it with:

```
python3 tools/charref/traits.py                    # validate, and preview 12 people
python3 tools/charref/traits.py --stats 6000       # distributions: catch soup and gaps
python3 tools/charref/traits.py --id B14823:2      # one person, identical every run
```

---

## 1. Which characteristics a rich world needs, and why

Every characteristic has to earn its place by doing at least one of these for the player:
- **Recognise:** tell people apart at a glance and remember them ("the tall woman with the
  red scarf").
- **Read:** infer who someone is before they speak (job, age, class, mood). This is Ghibli's
  strength (`ghibli_style.md` §1.1).
- **Find:** know where someone will be (schedule), and find them again.
- **Talk:** give dialogue something specific to say (preferences, history, opinions).
- **Play:** matter to quests and systems (skills, relationships, what they know).

| group | characteristics | recognise | read | find | talk | play |
|---|---|---|---|---|---|---|
| identity | sex, age, life stage | ● | ● | | ● | |
| role | occupation, income, workplace, household role | | ● | ● | ● | ● |
| body | height, build (triangle), weight, proportions, posture, mobility aid | ● | ● | | | |
| colour | skin, hair colour, greying, eye colour | ● | | | | |
| hair | style (silhouette) | ● | ● | | | |
| face | face shape morphs, brow, caricature, facial hair, marks (freckles, glasses, scars, weathering) | ● | ● | | ● | |
| clothing | outfit set per occasion, style, palette, one accent, wear, accessories | ● | ● | | ● | |
| motion | gait, idles, gesture amount, voice | ● | ● | | | |
| mind (L2) | personality (Big Five + warmth, humour, courage, honesty, curiosity), speech (formality, verbosity, dialect), preferences, values, fears, goals | | | | ● | ● |
| history (L2) | name, childhood and adulthood backstory, skills | | | | ● | ● |
| life (L3) | schedule, relationships, reputation, secrets, knowledge, possessions (vehicle, pet) | | | ● | ● | ● |

The literature supports this set:
- **Recognition** comes mostly from silhouette (hair, build, hat) and one colour accent.
  Ghibli crowds work that way, and Shadows of Doubt's describable features show what is
  gameplay-relevant.
- **Reading** comes from occupation-driven clothing and posture: Census's occupation → income →
  clothing chain, and Ghibli's working casts.
- **Talk** needs specific hooks. Dwarf Fortress's preferences show how cheaply they make
  characters distinct, and RimWorld's backstories give each person a past with consequences.
- **Find and play** need a schedule and relationships (Oblivion's packages, Talk of the Town).

Names, backstories, preferences and speech lists are for the **literary research phase**
that comes next. The schema already has the slots (`from_lists`).

---

## 2. The schema (one entry per characteristic)

```json
{"id": "height", "layer": "L1", "group": "body", "type": "float", "range": [0.8, 2.1], "unit": "m",
 "choose": {"normal": [1.63, 0.07], "clamp": [1.40, 1.95]},
 "mods": [{"if": "sex == 'male'", "add": 0.13},
          {"if": "age < 18", "mul": "0.52 + 0.48 * min(1, age / 17)"}],
 "depends_on": ["sex", "age"],
 "affects": ["shape:height", "gait.stride", "describe"],
 "describe": [[1.55, "short"], [1.80, "average height"], [9, "tall"]],
 "inherit": "blend"}
```

| field | meaning |
|---|---|
| `id` | unique name; also the seed of its random stream, so **never rename** a shipped trait (add a new one and retire the old) |
| `layer` | L0 core, L1 appearance, L2 persona, L3 life: when it is generated (`procedural_npcs.md` §2.2). A trait may depend only on its own or lower layers (the validator enforces this) |
| `group` | for tools and UI only |
| `type` | `pick` (one of `values`), `int`, `float`, `vec3/4/8` (morph vectors), `color2d` (a point in a colour ramp, as CK3), `tags` (a set), `map` (named numbers, e.g. personality), `rule` (game code), `text` |
| `choose` | how it is drawn (below) |
| `mods` | conditional changes, in order: `{"if": expr, ...}` with `add`, `mul`, `weights` (replace the table), `reweight` (change some entries), `bias` (add to Dirichlet parameters) |
| `depends_on` | traits read by `choose` or `mods` (checked for unknown names, layer order and cycles) |
| `affects` | what it drives: `shape:*` (body or face shape keys), `shader:*`, `mesh:*`, `anim:*`, `outfit.*`, `dialogue`, `placement`... This is documentation for now, and the generator's routing table later |
| `describe` | thresholds to words, for dialogue and descriptions |
| `inherit` | for families: `blend` (the average of parents plus noise), `pick` (one parent's), `none` |
| `version` | (optional) bump when re-tuning; people the player has met keep their saved values |

**Choosers:** `weights` (a weighted pick), `bands` (weighted ranges, e.g. age),
`table` (a weighted row of a table, filtered by `where`), `normal` (with `clamp` on the draw),
`uniform`, `uniform2` (with `bias_x` for colour ramps), `dirichlet` (the body triangle), `beta`
(0–1 skewed values), `each` (independent probability per tag; probabilities may be
expressions), `derive` (an expression of other traits), `from_lists` (lists from the literary
phase), `rule` (named game code, e.g. the schedule).

**Expressions** use only syntax shared by Python and GDScript: `a if c else b`,
`and`/`or`/`not`, `x in ['a', 'b']`, arithmetic, dotted access (`personality.extraversion`,
`row.age_min`), `min`, `max`, `clamp`, `abs`, `table(name, row, col)` and `rand_normal(mu, sd)`
(drawn from the trait's own stream). The game evaluates the same strings with Godot's
`Expression` class; the Python tool uses a sandboxed `eval`. Avoid chained comparisons
(`a <= b <= c`), which GDScript reads differently.

**Tables** hold shared rows: `occupations` (weight, sector, income, hours, outfit, age range,
caricature bias) and `palettes` (HSV swatches). Add a job by adding a row.

---

## 3. Rules that keep people coherent (anti-soup)
- **Chains, not independence:** occupation → income → style → wear; age → posture, gait,
  greying, brow, hat; occupation → build, weathering, caricature.
- **Replace, don't merge**, where a group changes the whole distribution (men's and
  elderly women's hairstyles use `weights`; tweaks use `reweight`).
- **One accent** at most (`accent_colour`), from the curated accent palette.
- **Exclusions and requirements:** as RimWorld does, via `mods` with weight 0 (no balding
  boys) and table `where` filters (occupation age ranges).
- **Check distributions, not individuals:** `--stats` over thousands. Run it after every
  change. It found two bugs while writing this (children with no occupation; children's
  heights clamped to the adult minimum).

## 4. Determinism and adding traits
Each trait draws from `splitmix64(fnv1a64("seed|person_id|trait_id"))`. Adding a trait
creates a new stream and leaves every other value alone. Verified: after inserting a new
trait, 2,000 of 2,000 people were otherwise identical, and the same person is identical on
every run. Changing a trait's distribution changes that trait and the traits that depend on
it. Saved deltas pin what the player has seen.

The GDScript generator must port `fnv1a64` and `splitmix64` bit for bit (64-bit wrapping
integer arithmetic). A DevBridge test should compare a few hundred people between the tool
and the game.

## 5. Where the numbers come from, and what to replace
- Age bands and income: the Stable Town archetype. The town's own archetype
  (`research/demographics/_demographic_archetypes.md`) should replace them per settlement.
- Occupation weights: a rough Midwest small-town job mix. They should come from each
  archetype's employment mix.
- Heights: approximate US adult means (female ~1.63 m, male ~1.76 m, SD ~0.07). The stylised
  mesh changes the proportions, not the height.
- Palettes: from `ghibli_style.md` §2.2 (saturation mostly 0.15–0.45). To be refined against
  `reference/ghibli/palette.json`.
- Everything else: first guesses, to be tuned by looking at crowds in-game.
