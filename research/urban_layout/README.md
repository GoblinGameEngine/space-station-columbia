# Urban layout research: for the settlement generator (2026-10-05)

The user, 2026-10-05: "begin research on city layout. Collect works on zoning, urban planning and gentrification.
Collect documents about traffic flow and suburban sprawl. We are going to build a procedural generation engine to lay
out our settlements. We were working on this before, let's take this time to expand the work."

| File | Covers |
|---|---|
| [01_zoning.md](01_zoning.md) | Euclidean zoning (Euclid v. Ambler), what a code controls per lot, form-based codes and the Transect (T1-T6), missing-middle types, parking minimums (Shoup), incrementalism |
| [02_urban_form.md](02_urban_form.md) | Burgess, Hoyt, multiple nuclei, bid-rent; Clark's density gradient; Christaller's hierarchy; retail catchments; Perry's neighbourhood unit; Lynch, Jacobs, space syntax; scaling laws; Warner's eras |
| [03_neighbourhood_change.md](03_neighbourhood_change.md) | Filtering and life cycle (Hoover and Vernon), gentrification (Glass, Smith's rent gap, UDP stages), Schelling sorting, redlining and the FHA |
| [04_traffic_flow.md](04_traffic_flow.md) | Fundamental diagram, BPR, the MFD; four-step demand model and ITE rates; functional classification and spacing; induced demand |
| [05_suburban_sprawl.md](05_suburban_sprawl.md) | The Ewing-Hamidi sprawl index; street-pattern eras and Boeing's measurements; Levittown; the strip and the edge city; SLEUTH growth |
| [07_centers_and_industry.md](07_centers_and_industry.md) | Strip, neighbourhood, community and power centres, lifestyle and open-air centres, industrial parks: the ICSC table, why each layout element is where it is, tenant mixes and why, siting rules; 10 measured Wisconsin examples; the generators (tools/settlegen/centers.py, in map_expanded's Harrow Falls) |
| [06_procedural_generation.md](06_procedural_generation.md) | Parish and Müller, tensor-field streets, layered editing, parcel subdivision, 4D growth, villages, SimCity; the shared pipeline |

## How this joins the earlier work

- **Built before**:
  - research/population_tiers/ and generator_rules.md: per-tier street, block and lot numbers.
  - research/roads/: the road standard, cross-sections and grading.
  - research/traffic/: driver behaviour.
  - research/lot_contents/: what is on a lot by income and era.
  - research/demographics/: community archetypes.
  - research/building_catalog, coastal_communities, hydrology_drainage.
  - The map: tools/map_preview.py, with map_expanded.py as the draft.
- **The map's settlements are still largely hand-written** in map_expanded.py: one `build_<town>()` each over a
  shared `build_town(pop, founding, archetype, layout)`.
- **The engine's job**: to replace those bodies with rules, while the map keeps its authority over *where*
  settlements, water and highways are (memory: the map is the only layout authority).
- **generator_rules.md is out of date**: it describes the old 500 m `SpaceStation.gd` ring. Its per-tier tables are
  still good, but the geometry needs rewriting for the map.

## What the research says the engine should be (draft for discussion)

### 1. Knobs per settlement

- **Population** sets the Christaller tier: which services exist and how many stores.
- **Founding era** (walking / rail / streetcar / auto) sets the oldest band's street pattern, the steepness of the
  density gradient, and lot widths.
- **Growth eras**: which later bands wrap it. Each era has its pattern, its block size and its parking share.
- **Archetype**: the existing demographic archetypes (resort, farm town, mill town, port).
- **Water and terrain**, from the map.

### 2. Fields: local, closed-form, evaluated per chunk

- **Transect value T(x)** (T1-T6): from distance to the centre and to secondary nuclei (Burgess plus multiple
  nuclei), bent along the highways and rail (Hoyt).
- **Era band E(x)**: which growth era built this ground.
- **Price P(x)**: bid-rent from accessibility, amenity (water, parks, high ground) and nuisance (rail, industry).
- **Street tensor field**: a grid basis per era band, blended with boundary-following fields along the shores,
  rivers and rails (Chen et al. 2008).

### 3. Network, once per settlement

1. Arterials from the map's highways.
2. Collectors at the FHWA spacing.
3. Locals traced from the tensor field per era band.
   - Grid bands keep 4-way junctions.
   - Postwar bands use loops and culs-de-sac to the measured targets (05: node degree, dead-end share,
     intersection density).

### 4. Parcels and uses, per block (local)

- **Subdivision**: OBB or straight-skeleton split, with lot width and depth from T and E (01).
- **Use**:
  - Commerce takes the most integrated frontage (space syntax).
  - Shopping-centre types sit at arterial corners by catchment (02).
  - Industry goes along rail and water.
  - Schools follow neighbourhood-unit spacing.
- **Output**: building *type and slot* only, never a model (memory: ssc-build-order).

### 5. Time: the story engine's hook

- **Each district carries state**: age, condition, price, tenure and investment grade.
- **Yearly steps**: decay, filtering, the rent gap leading to renovation, infill and gentrification, increments
  (Strong Towns), and Schelling moves among NpcLife households.
- **What it changes**: lot contents, storefront turnover and residents, all visibly.

### 6. Checks: tests like the vehicle fleet's

- The Ewing-Hamidi four dimensions per district.
- Boeing's network measures per era band.
- Road length against population^0.85.
- Trip generation per dwelling, with BPR loads on the arterials at peak.

## Decisions (the user, 2026-10-05)

1. **Era bands.** Towns grow in real bands (walking / rail / streetcar / auto, roughly 1850-1980), each with its own
   streets, lots and parking.
2. **The station has its own history.** "We are not trying to fight the battles of America's past." Neighbourhood
   change keeps its *mechanisms* (credit by district grade, sorting, the rent gap, filtering), but the institutions,
   groups and prejudices come from the station's bible, not from Earth's redlining or racial history.
3. **Baked once.** A town's history (growth bands, decay, gentrification, sorting) is simulated when the world is
   baked, not during play. Iterative models (SLEUTH, the 4D growth step, Schelling) are fine at bake time. The baked
   result must still be deterministic per seed.
4. **The station will grow to 100 km long and 20 km in diameter** (radius 10 km, circumference about 62.8 km, so
   about 6,280 km² of floor). This research will eventually fill that map. "We are not there yet": map_expanded.py's
   3 km ring is not the target, and the map isn't being changed now.
   - At that size, Christaller's hierarchy and spacing (02), the arterial and highway network (04) and the growth
     models (05) matter at full scale: tens of settlements, county-style road grids, and most of the land in farms.

## The first generated town: Calder (2026-10-06)

The user, 2026-10-06: "using our research, create a new city in the open countryside. This will be a 1:1 scale city
of 7,000 people. The buildings will all be unique, generated by the rules we just defined. I want it to have an
Elementary School, High School, Hospital, four properly sized strip malls in town and three in the surrounding
countryside. Name the town and name the streets and name the shopping centers. There also needs to be a small
downtown section with the Post Office, city hall, police station and fire department."

**Where:** on US 30 and the Ring Line, on the southland's open farmland between Bellhaven and Pruett (s 6,890-8,710,
x 640-2,500). The section line s = 7,516 is its Calder Ave / Calder Rd. Canon: tools/bible/canon_world.py (founded
VY 186 round Ines Calder's infirmary; the southland's hospital town; governed by Kessler's law).

**How (tools/settlegen/town.py, calder.py, records.py):**
1. **Network first, by era band** (README decision 1):
   - rail-era Main Street (US 30) parallel to the tracks, with the depot on them;
   - the old grid of 300 ft blocks (112 m centre to centre) with alleys;
   - interwar wings without alleys;
   - the South Side workers' grid across the tracks;
   - postwar curving streets (FHA);
   - 1990s-2010s curving subdivisions;
   - collectors round the town (Bluff Dr, Southview Dr, Deer Creek Rd, Birch Run Rd, River Rd / Calder Rd).
2. **Sites:**
   - the civic square (City Hall, Police, Fire, Post Office, Library);
   - the hospital campus at the east entry on US 30;
   - the elementary at the neighbourhood's centre (Perry);
   - the high school campus with its fields;
   - the four in-town centres from centers.py (a community centre and a neighbourhood centre at the US 30 entries,
     convenience strips at collector corners);
   - parks, the cemetery and the water tower.
3. **Lots along every frontage** by the band's width, depth and setback (LOTS §5):
   - an occupancy raster keeps lots off streets and each other;
   - squeezed lots get shallower before they're given up;
   - a block face shares its setback.
4. **Housing mix:**
   - doubles and two-flats in the old grid;
   - town-house rows and garden apartments in the newest streets and at collector corners (01, missing middle);
   - flats over the downtown stores.
5. **A record per building** (records.py):
   - the house's form, storeys, walls, porch, roof, windows, garage, fences, colours and condition are drawn from
     its band;
   - the Great Lakes token corpus is blended with the style priors;
   - its block face's theme (03 compatibility) applies;
   - every house is unique.
6. **Names:**
   - streets: Main St, 1st-5th St, cross streets of trees and southland families, courts and drives;
   - centres: Calder Commons, Westgate Plaza, Southview Center and Bluff Shoppes in town; Birch Run Plaza, Deer
     Creek Corners and Pruett Crossroads in the countryside;
   - institutions: Calder Memorial Hospital, Ines Calder Elementary, Southland High School;
   - businesses: from the bible's family names.

**Numbers (seed 186):**
- 1,714 structures: 1,322 houses, 105 doubles and two-flats, 106 town-house rows, 58 apartment buildings, 62
  downtown stores, and the institutions and centre buildings.
- About 3,000 dwelling units, so 2.4 people per household with 4 % vacancy gives about 7,000 people.
- 46 km of streets.
