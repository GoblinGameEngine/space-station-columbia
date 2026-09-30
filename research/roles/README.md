# Roles in the world

This is the roles layer of the story engine. Research on roles in contemporary suburban and urban
middle America, and on roles aboard large enclosed stations. It produces an exhaustive, tokenized
catalogue of roles and shows how they drive ties, knowledge, spread, judgement, stress, stories and
dialogue.

The user's brief (2026-09-30): research roles in the world, in contemporary suburban and urban
middle America, and scholarly work on the roles of people aboard large enclosed space stations like
ours, as another exhaustive list.

## Files
| file | what it holds |
|---|---|
| [01_role_theory.md](01_role_theory.md) | Linton (status and role; ascribed and achieved), Merton (role set), Goode (role strain), Hughes (master status), Bales and Johnson (task and heart leadership), Katz & Lazarsfeld (opinion leaders), Burt (brokers), di Leonardo (kin-keepers), Jacobs and Duneier (public characters), Oldenburg (third places and regulars), Small and Klinenberg (institutions broker ties) |
| [02_middle_america.md](02_middle_america.md) | Middletown (business and working class), *The Levittowners* (new communities build institutions fast), Putnam; 2023–25 data: BLS largest occupations, AARP caregivers (about 1 in 4 adults), AmeriCorps (54% help neighbours, 28% volunteer), Gallup (3 in 10 attend services), Census (29% live alone), NORC/GSS prestige |
| [03_space_station_roles.md](03_space_station_roles.md) | NASA SP-413's colony population; *Living Aloft* (SP-483); Stuster's *Bold Endeavors* (communal meals, the cook as a morale role); Johnson's Antarctic informal roles (clowns, leaders, buddies, storytellers, peacemakers, counsellors; consensus on roles means cohesion); Palinkas (Biomed/Library/Bar cliques; clique crews fare worse); McMurdo (science and support classes, a US Marshal); Biosphere 2 (factions in a functioning team) |
| [04_role_catalogue.md](04_role_catalogue.md) | **The catalogue: 136 roles in 6 families**: household and kin; middle-American work; station roles; civic; informal (emergent); life stage and status. Each has its frequency, prestige, prominence, knowledge channels, role set, duties, story hooks (all validated against the story catalogue) and its station form |
| [roles.json](roles.json) | the same catalogue for the engine |
| [05_roles_in_the_engine.md](05_roles_in_the_engine.md) | **The framework:** `RL.` tokens; allocation (settlement needs, many hats, joiners, vacancies); informal roles computed from network position; **cohesion by consensus on critical roles**; how roles feed ties, knowledge, propagation, appraisal, stress, stories and dialogue |

Generator: `tools/story/make_roles.py`. Prototype: `tools/story/roles_proto.py` (informal roles
and cohesion across generated settlements). Local sources in `reference/roles/` (gitignored).
