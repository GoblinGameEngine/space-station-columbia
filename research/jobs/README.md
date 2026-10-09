# Jobs: offices, industry and staffing (2026-10-08)

The user, 2026-10-08: "lets add the office space and industrial centers. You can trade out retail space if there is too
much of it."

## What the lives bake shows
These are the figures from the last full lives bake (218,167 people). Every settlement with room manifests is its own
labour market (NpcOccupancy): a resident works in their own town or not at all. Posts are filled by occupation.

| Occupation | People | Posts | Short |
|---|---|---|---|
| shop clerk | 11,151 | 2,735 | 8,400 |
| factory hand | 9,682 | 3,354 | 6,300 |
| clerk | 8,545 | 4,459 | 4,100 |
| nurse | 7,517 | 367 | 7,150 |
| care aide | 6,345 | 282 | 6,060 |
| cook | 5,684 | 1,128 | 4,550 |
| janitor | 5,519 | 400 | 5,100 |
| waiter | 5,435 | 2,179 | 3,250 |
| farmer + farmhand | 8,721 | 102 | (farms: their own place, see below) |
| teacher | 4,323 | 888 | 3,400 |
| builder | 3,997 | 0 | 4,000 |
| mechanic | 3,193 | 483 | 2,700 |
| driver | 2,927 | 356 | 2,550 |
| hotel worker | 2,843 | 6 | 2,850 |
| fisher | 2,728 | 0 | 2,700 |
| dock worker | 2,456 | 20 | 2,450 |
| banker, lawyer, doctor, editor... | ~9,000 | ~1,300 | ~7,700 |
| **agent** (insurance) | 6,066 | **6,236** | **over** |

About 128,000 people hold a working occupation and 26,270 of them are employed. Solana Point, at 42,929 people, has
3,132 posts.

Too many shops is not the problem; too few staff in each one is. Every storefront holds a fixed 2–4 people, while the
insurance office, the default for every office above a shop (3,118 of them), is the only trade with more posts than
people.

## Why
1. **Staffing is a fixed headcount per place type** (`npc_places.json` jobs, `make_rooms.posts_for`). A corner grocery
   and a 4,000 m² supermarket each get 4 clerks. A hospital has 61 nurses whatever its size.
2. **There is almost nowhere to work at scale.** There are 13 industrial structures and 7 big boxes in the world. No
   office buildings exist, only upstairs offices. There are no care homes, and hotels are few.
3. **The upstairs office is always "insurance"**, the only office type with that shell.

## Planning densities (what a building of a kind employs)
These are planning standards in floor area per employee:
- office 300 sq ft (28 m²)
- R&D 340 sq ft
- light manufacturing 435 sq ft (40 m²)
- warehouse and service industrial 560 sq ft
- retail 510 sq ft (47 m²)
- restaurant 170 sq ft (16 m²)
- hotel 1,370 sq ft (127 m²)

From the Snohomish County employment density study (sq ft per employee):
- manufacturing 500
- wholesale, transport and utilities 1,000
- finance, insurance and real estate 350
- services 400
- government and education 300
- food services 200

CBECS 2018 medians run higher (office 609 sq ft per worker, warehouse 2,000) because they average over part-empty
stock.

Sources:
- [Pleasanton planning table](https://weblink.cityofpleasantonca.gov/WebLink/0/doc/304851/Page22.aspx)
- [Snohomish County Employment Density Study](https://snohomishcountywa.gov/DocumentCenter/View/7660/Employment-Density-Study)
- [Metropolitan Council: measuring employment intensity](https://metrocouncil.org/Handbook/Files/Resources/Fact-Sheet/LAND-USE/How-to-Measure-Employment-Intensity-and-Capacity.aspx)
- [UK HCA employment densities](https://assets.publishing.service.gov.uk/media/5a7dedd8e5274a2e8ab44baf/employ-den.pdf)
- [CBECS 2018 B16](https://www.eia.gov/consumption/commercial/data/2018/bc/pdf/b16.pdf)

Industrial parks are in [urban_layout/07](../urban_layout/07_centers_and_industry.md): their building types, siting,
coverage of 35–45 % and the `centers.industrial_park` generator. Industry canon (remelting, rolling, tube, casting,
machining, motor winding, cell works, tyres, glass, gauges, Wire sets, the three vehicle works, the Drops) is in
[bible/12](../bible/12_industry.md).

## The plan
1. **Staffing by floor area.** Each place type gets a reference floor area. A unit's headcount is its type's jobs scaled
   by the unit's floor area from its room manifest over that reference, floored at the type's minimum. This is applied in
   `make_rooms.posts_for`. The bigger a store, ward block or school, the more people work there.
2. **Upstairs offices by demand, not one type.** The office types come from canon:
   - the Registry's branch offices
   - the Board Office
   - the Wire's studios
   - engineering and drafting
   - accounting
   - cab and haulage dispatch
   - the Courier (newspaper)
   - architects
   - the College's extension offices
   - insurance, law, doctors and dentists, as now
3. **Office blocks downtown.** In cities and county seats, a share of the downtown store lots nearest the heart
   become office blocks of 4–10 storeys (`store.py` form `office_block`). Each floor is a tenant unit. This is the
   retail trade the user allowed: these lots were storefronts.
4. **Industrial districts.** Each town gets one or more `centers.industrial_park` sites at its edge, by the rail or
   the highway, opposite the affluent side, sized to the town's factory, driver, dock, builder and mechanic shortfall:
   - manufacturing shops and works, built by `works.py` in a large mode up to 120 × 80 m;
   - warehouses, contractor yards, truck terminals;
   - each works named for canon industries.

   Port Carrow and the harbours add dock warehouses and fish houses. Harrow Falls, Port Carrow and Solana Point keep
   their vehicle works.
   Where a city is built out to its edge and the parks fall short, its **old works district** takes the rest:
   - store and apartment lots by the rail, or round downtown's edge, become 3–5 storey works lofts (`works.py`);
   - at most 80 lots, skipping about a third, so the street keeps some of its life.

   In the dry run, Kessler gets 2 parks and 41 lofts, and Marlowe 1 park and 25 lofts; both meet their targets.
5. **Care homes, hotels, schools and hospitals sized to need.** Care aides and nurses get care homes (one bed per ~80
   people over 75) and hospitals scaled by beds. Teachers are scaled by pupils.
6. **New structures are appended after the existing ids** (`city.structures`), and office conversions keep their lot's
   id, so every existing model, LOD and manifest stays valid. The city plans are re-run, but the post-pass has its own
   seeded RNG and leaves the existing random streams unchanged.

Rebake chain: `map_expanded --game-data` → records → `build_library` (new models) → gblod → import → placement →
`bake_world` → `bake_places` → `make_rooms` → `bake_paths` → `bake_lives` → `make_vehicles`, then the far-side bake
and the export (`tools/regen_world.sh`).

## Gotcha: the plan cache
`map_expanded._plan_cached` used to fall back to the plans cached under the first key (`plan_cache/city_key_v1.py`)
whenever the current key missed. Every planner change after that silently got the old plans back. The fallback was
removed on 2026-10-08, so planner edits now really re-plan, at about 10 minutes a city.

## Results (2026-10-09 regen)
| | Before | After |
|---|---|---|
| Posts (room manifests, all towns) | ~27,400 | 80,128 |
| Employed | 26,270 | 72,923 (56 % of the 129k with a working occupation) |
| Solana Point posts | 3,132 | 11,428 |
| Port Carrow posts | 5,871 | 14,094 |
| Population (place index) | 242,366 | 238,287 |
| Structures placed | 63,021 | 63,372 |

Solana Point gets 19 office blocks, 2 industrial parks and 128 works lofts. Factory hands (18,054 of 18,397) and clerks
(14,864 of 14,867) now nearly all work.

Still short:
- nurses (2,004 of 7,405) and care aides (402 of 6,256): care homes, and hospitals sized to beds;
- janitors (920 of 5,403);
- shop clerks (4,091 of 10,910) and shopkeepers;
- teachers (1,251 of 4,265);
- hotel workers (6 of 1,034) and fishers (0 of 718);
- farmers and farmhands (4 of 2,651): an old bug in the farm-family assignment.

These are next.

Gotchas found on the way:
- A second `_pods` call re-laid pods over the first ones, and placement left out 6,000 buildings. Households lost to the
  conversions are now restored by raising inner apartments to big blocks on the same lots.
- An industrial park's frontage street and connector must be checked against the occupancy too.
- `map_expanded.py` needs its PNG output argument (`map_expanded.py OUT.png --game-data`).
