# 10. How the engine uses the bible

| file | used for |
|---|---|
| names.json | NpcNames: a household's surname (weighted by the town's heritage leans and the lineage strongholds) and each member's given name (sex, birth year's cohort mix, family heritage), plus nicknames |
| lineages.json | a surname's lineage gives trade and faith tendencies, temperament tilts, lore lines for dialogue, and feud and alliance priors |
| settlements.json | full-scale town facts: archetype, heritage and faith leanings, rivals, reputation (dialogue: 'Pointers are loud') |
| history.json | what a person knows (the knowledge level x their age, schooling, faith and family), and the popular versions to quote; living memory by birth year; the Moderators and Spin Cups for small talk |
| people.json | living notables pinned into the world (home, occupation, age, sex, family); the dead as memory and reputation; descendants through lineages |
| factions.json | membership by the `draws` rules; affinity priors (09) |
| culture.json | holidays drive NpcLife (closures, parades, church); foods drive places' stock; lexicon and sayings go to the dialogue prompt; beliefs weight what a person thinks of the Notice |
| world.json | the frame of every prompt: the date (VY 500), the Steward, the calendar, the land |

## Counts

- events_past: 133
- events_future: 17
- eras: 17
- people: 129
- people_living: 74
- lineages_major: 50
- lineages_minor: 76
- factions: 16
- settlements: 23
- vehicle_companies: 3
- boards: 4
- holidays: 30
- foods: 46
- lexicon: 64
- beliefs: 20
- moderators: 99
- spin_cups: 299
- surnames_2752: 8173
- extinct_surnames_listed: 4000
- given_names: 10103

## Rebuild

`python3 tools/bible/make_bible.py`: names, canon, checks, JSON and these pages, in about 15 s. It fails on any broken reference.
