# The Columbia game bible

The canon of Space Station Columbia as **data for the procedural engine**: names, history, people, families, factions, culture, places and the outside world.
It is built from `tools/bible/canon_*.py` and the downloaded name data by `tools/bible/make_bible.py`, which checks every cross-reference.
The build writes the engine files to `godot_project/remake/bible/*.json` and these pages.

**The premise (the user, 2026-09-30):**
- Columbia is an ark ship on a 1,500-year voyage to another star, launched from Earth in 2252.
- It is a self-contained, balanced world.
- The game is set 500 years after launch (VY 500, 2752). People only vaguely know why they are aboard or where they are going.
- The founders came from the southern Great Lakes and reflect the diversity of the whole continent.
- 250,000 people live aboard (the test towns hold a small sample).
- The station lasts 3,000 years.
- Every vehicle is electric or pedal-powered, and trams run on roads.
- The player is from somewhere else aboard. The user chooses where.

## Contents
| page | engine file | what |
|---|---|---|
| [01_world.md](01_world.md) | world.json | the ship, the voyage, the Steward, the calendar, the land, the population, the institutions, faiths, languages, what people know |
| [02_names.md](02_names.md) | names.json | 8173 surnames alive in 2752 (from 20851 founding surnames), given-name pools and the cohort mixes, nicknames |
| [03_history.md](03_history.md) | history.json | 17 eras, 133 past events (year by year in living memory), 17 future events, every Moderator, every Spin Cup |
| [04_people.md](04_people.md) | people.json | 129 important people (74 living): native or immigrant, marriages, children or why not, deeds, reputation |
| [05_lineages.md](05_lineages.md) | lineages.json | 50 great families and 76 minor lines: trades, faith, temperament, lore, feuds and alliances |
| [06_culture.md](06_culture.md) | culture.json | holidays, foods, rites, customs, the lexicon, sayings, beliefs, superstitions, etiquette, taboos, pastimes, arts, dialect, and what changed from Earth |
| [07_settlements.md](07_settlements.md) | settlements.json | the 21 towns at full scale: population, founding, character, districts, heritage and faith leanings, landmarks, rivals |
| [08_outside_world.md](08_outside_world.md) | history.json (scope earth) | Earth before the launch, the Earth-link, the other arks, the destination, the future |
| [09_affinity.md](09_affinity.md) | factions.json | factions and the **affinity model**: priors between people and toward the player, and what's stored |
| [10_engine.md](10_engine.md) | schema.json, index.json | how the engine uses each file |
| [12_industry.md](12_industry.md) | industry.json | the Rock and the Spindle, the Drops, what the Steward makes and the limits it keeps (the Thirty-Two, panels, gauges, the Wire slot), the boards, how things are made, the three vehicle works and their histories |

## Sources
- **Surnames:** the 2000 US Census surname file (151,671 names, with ethnic shares), via fivethirtyeight/data.
- **Given names:** SSA baby names 1880-2017 (every name given to 5 or more births in a year), via hadley/babynames.
  The census.gov and ssa.gov servers refuse scripted downloads, so the files come from GitHub mirrors. The raw files are in the gitignored `reference/names/`.
- **The project's own research:**
  - `research/demographics` (Great Lakes community profiles);
  - `research/psychology/03_frontier_and_space.md` (frontier and isolated-environment psychology);
  - `research/roles` (roles in middle America and aboard stations);
  - `research/story` (story types);
  - `research/coastal_communities` (the towns' real-world models).
- **Generation ships:** Moore 2002/2003 (a crew of about 160, or 80 with delayed childbearing, for 200 years); Smith 2014 (tens of thousands, allowing for catastrophes); Marin & Beluffi 2018 (a minimal crew for Proxima b); Project Hyperion (i4is; 2024-25 competition won by *Chrysalis*). All via Wikipedia, *Generation ship*.
- **Destination:** Alpha Centauri at 4.34 ly; A is a G2V star at 1.51 times the Sun's luminosity, with a habitable zone of about 0.9-1.5 AU (Wikipedia, *Alpha Centauri*). **Hesper is fiction.**
- **Habitat form:** O'Neill's cylinders (*The High Frontier*, 1976; NASA SP-413, 1977).
- **Collective memory:** Jan Assmann's communicative memory (about 80-100 years, three generations) and Jan Vansina's 'floating gap' (*Oral Tradition as History*, 1985). **From knowledge:** the Wikipedia pages fetched didn't carry these details.
- **Great Lakes communities:** Polish (Chicago, Detroit/Hamtramck, Buffalo's Dyngus Day, Milwaukee), Hungarian (Cleveland's Buckeye Road, Toledo's Birmingham) and Arab (Dearborn) communities, via Wikipedia.
- **Inland North dialect:** 'pop', 'party store', 'doorwall', 'gapers' block', 'bubbler', and the Northern Cities Vowel Shift (Wikipedia, *Inland Northern American English*).
- **Knowledge, not fetched:**
  - Quebec surnames and the heritage given-name lists;
  - the founders' ancestry mix (a canon extrapolation, not a forecast);
  - the Indigenous given names, which **must be reviewed with community sources**.
