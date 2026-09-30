# Story: stories about people, what makes them good, and arcs in the engine

This is the story layer of the story engine. The psychology framework (`research/psychology/`)
decides what each person knows, feels and wants. This layer recognises when that is a **story**,
casts people in **roles**, advances **beats**, paces them like a storyteller, and records the
player's history as a **chronicle of arcs**. Dialogue gets a `[STORY]` section: the dramatic
situation, not a script.

The user's brief (2026-09-30):
- research stories about interpersonal relationships, looking up and reading the definitive works;
- research what makes a good story;
- build an exhaustive list of the types of good stories;
- tokenize the story points;
- the player's history follows a series of story arcs, and this is the framework they follow;
- fit it into the procedural generation engine.

## Files
| file | what it holds |
|---|---|
| [01_definitive_works.md](01_definitive_works.md) | Reading notes and what the engine takes from each: Aristotle's *Poetics* and Freytag (read in full), Polti's 36 situations with their required roles, Propp, Greimas, Todorov, Campbell and Vogler, Frye, Booker, Tobias, Egri, McKee, Regis, kishōtenketsu, Reagan's six arcs, the ATU index, the interpersonal canon (*Spoon River* analysed as a network, *Winesburg*, *Middlemarch*, Shakespeare), and game story systems (Façade, storylets, RimWorld, story sifting) |
| [02_what_makes_a_good_story.md](02_what_makes_a_good_story.md) | Evidence and craft principles, each as an engine test, combined into `ST.quality` |
| [03_story_types.md](03_story_types.md) | **The catalogue: 76 story types in 7 families**, on 10 beat templates. Checked coverage of all 36 Polti situations, Booker's 7 plots and Tobias's 20 |
| [story_types.json](story_types.json) | The same catalogue for the engine: roles (actants and eligibility), trigger, beats (stage, tension, function), shape, mythoi, value, theme, sources, reach |
| [04_arcs_in_the_engine.md](04_arcs_in_the_engine.md) | **The framework:** story tokens (`ST.`); the arc life cycle (sift, cast, merge, admit, beats, fade, resolve, sequel, chronicle); degrees of separation (the chorus); the drama manager and storytellers; the `[STORY]` prompt section; prototype results |

Generators: `tools/story/make_story_types.py` (the catalogue and its coverage check) and
`tools/story/make_tokens.py` (all 166 tokens).

Prototype: `tools/story/arc_proto.py`. A settlement plays out 60 days of player actions. Arcs are
sifted, merged, featured or backgrounded, advanced and resolved, under two storytellers. It prints
the player's history as arcs and a sample `[STORY]` card.

Source texts live in `reference/story/`, which is gitignored.
