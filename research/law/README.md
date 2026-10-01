# The station's laws of the street

Built by `tools/law/make_law.py` from `tools/law/canon_law.py`; the engine reads `godot_project/remake/law/*.json`.
These pages are the source for the in-game lawbooks and legal system to come.

| page | what |
|---|---|
| [01_state.md](01_state.md) | the state baselines (Ohio Revised Code; Indiana for Oceanview) |
| [02_cities.md](02_cities.md) | the six large cities' ordinances: parking, sidewalks, streets, speeds, transit stop flags |
| [03_settlements.md](03_settlements.md) | every settlement, its tier, the city whose law it follows, and fast-travel |
| [04_signs.md](04_signs.md) | the sign catalogue (MUTCD codes) and each city's transit stop flag |
| [05_subdivisions.md](05_subdivisions.md) | the Regional Planning Boards' subdivision rules |
| [06_zoning_and_building.md](06_zoning_and_building.md) | zoning districts and the building code tokens |
| [07_planning_literature.md](07_planning_literature.md) | walkable, urban and suburban development: the scholarship and the rules taken from it |

## Sources and their weight
- **Fetched (2026-10-01):** the Ohio Revised Code from codes.ohio.gov (4511.21, 4511.68, 4511.69, 711.05, 711.10, 729.01, 3781.01); the MUTCD's Part 2B (FHWA); Wikipedia's pages on walkability, New Urbanism, suburbanisation, transit-oriented development, the cul-de-sac and Jacobs's book.
- **Not reachable:** the cities' codified ordinances. Municode and American Legal refuse automated readers, and the session's web-search budget ran out. Each city's variant is therefore **the station's own law**, modelled on what its basis city is known for and on common Ohio and Indiana municipal practice. Nothing here claims to quote a real city ordinance.
- **From knowledge (marked):** the Indiana Code baselines; the model building codes' numbers (IBC/IRC as adopted by Ohio and Indiana: the ICC texts are copyrighted); subdivision and zoning values in the range Ohio and Indiana regulations use.
- A later pass with web search can check the city rules against the real ordinances and replace any that should follow them more closely.
