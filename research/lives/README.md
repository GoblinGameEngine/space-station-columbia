# Daily lives: places, money, addiction, travel

People live their lives attached to buildings. They live in one, work in another, shop in others,
and travel between them every day, often to different ones. This folder is the research and design
for that layer of the character generator, together with the granular life facts the dialogue
model needs: money, addiction, habits, where someone is and why.

The user's brief (2026-09-30):
- account for homes, workplaces and shops, and daily travel between them;
- record the building types in a file, so the attributes can be added to our buildings;
- give people different amounts of money, for different reasons;
- give some people addictions, from social media to gambling to drugs;
- account for walking, cycling and public transit, with widespread car ownership;
- building purposes are procedural (signage and contents). The engine says what *type* of thing
  goes where, not which model;
- build order: this engine first, then the game bible, then the models, built to the engine's
  contracts.

## What was missing before this round
- Homes were assigned (NpcHouseholds). There were no workplaces, schools, shops or leisure
  places, and no daily schedule; the `schedule` trait was a placeholder.
- Money was a four-step income band (none, low, mid, high).
- There was no addiction at all.
- People stepped out of their doors at random and walked up and down the street.

## Files
| file | what it holds |
|---|---|
| [01_building_types.md](01_building_types.md) | **The building-types contract** (generated): 21 shells, 80 place types, each with its jobs, hours, visits and **contents slots** (fixtures, stock families, machinery, signage), plus 12 station facility types |
| [02_money.md](02_money.md) | wage, savings, debt, what the debts are, why people have what they have, money style, and the finances band; calibration against the Fed SHED |
| [03_addiction.md](03_addiction.md) | 13 addictions, from nicotine to social media, gambling and opioids; stage and severity; prevalence targets; how to portray it without stigma |
| [04_travel.md](04_travel.md) | car access, usual commute, mode for each trip, the walking network |
| [05_daily_life_engine.md](05_daily_life_engine.md) | **The engine:** place units and their procedural purposes; anchors (work, school, regular places); the day plan; where someone is at any hour; population in the game; the `[LIFE]` prompt card |
| [06_vehicles.md](06_vehicles.md) | **The vehicle contract** (generated): 141 vehicle types in 13 groups, with who uses each, where it lives, size, seats, states, variants, the NPC actions it needs, priority, and how many the present station needs |

## Code and data
| what | where |
|---|---|
| building-types registry | `tools/places/make_places.py` → `godot_project/remake/characters/npc_places.json` |
| place units (procedural purposes) | `tools/places/bake_places.py` → `npc_place_index.json` |
| walking network | `tools/places/bake_paths.py` → `npc_paths.json` |
| vehicle contract | `tools/places/make_vehicles.py` → `npc_vehicles.json` (after bake_lives) |
| everyone's anchors | `godot_project/remake/tools/bake_lives.gd` → `npc_lives.json` |
| the day plan, travel, `[LIFE]` card | `godot_project/remake/characters/npc_life.gd` (NpcLife) |
| places, opening hours, routes | `godot_project/remake/characters/npc_places.gd` (NpcPlaces) |
| money, addiction, travel and worship traits | `npc_traits.json` (Python/GDScript parity: 0 mismatches) |
| calibration | `tools/charref/life_stats.py`; `godot_project/remake/tools/npc_life_test.gd` |

**Rebake order** after changing traits, households, placement or places:
1. `make_places.py`
2. `bake_places.py`
3. `bake_paths.py` (only needed after road changes)
4. `bake_lives.gd`
