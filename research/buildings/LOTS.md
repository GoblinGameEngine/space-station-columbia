# Lots: how they are sized, shaped, arranged and marked (2026-10-05)

The user, 2026-10-05: "I want you to also tokenize the lots. Lots are a certain size in relation to the building(s)
on it and are demarcated from the surrounding lots with fences, different grass, bush and tree lines, etc. Tokenize
this and analyze how and why they work. We need to have a fine fundamental understanding of how lots are sized and
arranged for all circumstances."

Three kinds of evidence go into this file:

1. **Measurement**: 21 sample areas of real Wisconsin lots (~2,900 parcels), from the statewide parcel layer, OSM
   buildings and streets, and NAIP aerials (`tools/buildings/lot_sample.py`). Per-lot data and tokens are in
   `regions/great_lakes/lots/<area>.json`; renders in `reference/lots/great_lakes/` (local).
2. **Observation**: the aerials and the tokenized photos (`regions/great_lakes/tokens/`), for boundaries.
3. **History and rules**: why the numbers are what they are (below), building on `research/lot_contents/` (what is
   on a lot), `urban_layout/` (blocks and streets) and `regions/great_lakes/01_codes.md` (setback rules).

## 1. Why lots are the sizes they are

| Force | Rule | What it does to the lot |
|---|---|---|
| **The survey grid** (PLSS, 1785) | Townships of 36 sections; a section of 640 acres, halved and quartered: 160 (the quarter), 40 (the quarter-quarter); errors pushed into the north and west "lots" | Every rural parcel in the Old Northwest is an **aliquot** of the mile grid (40, 80, 160 acres). Roads run on the section lines (1 mile apart), so farms and their houses sit on the mile-grid roads. Town plats are laid inside quarter-sections |
| **The chain** (66 ft) | The surveyor's unit; streets of 66 ft (one chain) | 19th-century plats: 66 ft streets, blocks of 300-400 ft, lots of 33 x 132 ft (half a chain by two), 50 x 150 ft, or Chicago's **25 x 125 ft**. The narrow lot is a fraction of the chain |
| **Frontage pricing** | Lots sold and taxed by the front foot | Narrow and deep lots: buyers paid for frontage, so lots got deep and narrow (the 30-40 x 120-130 ft streetcar lot). The house fills the width, gable to the street |
| **The alley** | 16-20 ft service lane mid-block | Garages, coal, ash and later trash at the rear; the front stays a clean face. **78 % of Bay View's lots touch an alley** (measured) |
| **Fire and light rules** | Side yards for light and fire (tenement laws; IRC R302 today: 3-5 ft) | Minimum side gaps of 3-5 ft; houses never quite touch except row houses with fire walls |
| **The car** (1920s on) | A driveway needs ~10 ft; a garage door needs width | Lots widen: 40 ft (1910s) → 50-60 ft (1920s-40s) → 75-100 ft (1950s-70s ranch). The garage moves from the rear (alley) to the side, to the front of the house |
| **FHA standards** (1934-60s) | Insured mortgages only on approved subdivisions: wide lots for "light, air and driveways", 50 ft rights of way, curving streets | The postwar tract: 60-75 ft x 100-130 ft, no alley, a driveway per lot |
| **Zoning minimums** | Median minimum lot size rose from ~5,000 sq ft (1920s) to ~7,500 sq ft (1970s); suburban R-1 zones 10-20,000 | Lot size is set by law per district, not by the market; exclusionary zoning drives very large exurban lots |
| **Septic systems** | An unsewered lot needs room for a drain field and a reserve area: commonly ½-1 acre or more | **Rural and exurban lots of 1-5 acres** (the "acreage" lot on county roads) |
| **Subdivision economics** (1970s-2010s) | Developers fit as many lots as zoning allows on curving streets; culs-de-sac sell at a premium | **Pie-shaped lots** on bulbs and curves; the "irregular" share rises to a third or more (measured below) |
| **New Urbanism** (1990s-) | Narrow lots, alleys, garages at the rear, houses near the street | Middleton Hills: 21.5 x 31 m lots, 74 % with alleys, coverage 0.57 (measured) |
| **Condominiums and land-lease parks** | The owners hold units; the land is one common parcel (condo) or leased (mobile home park) | **One huge parcel with many buildings**: the Fitchburg condos' "lot" is 280 x 152 m; the mobile home park is a few big parcels |
| **Commercial: pads and outparcels** | Centres split into the anchor parcel and pads sold or ground-leased at the road (07_centers_and_industry.md) | Irregular and flag-shaped commercial parcels round the parking field (the mall: 20 % flag-shaped, measured) |

Sources: [Section (US land surveying) (Wikipedia)](https://en.wikipedia.org/wiki/Section_(United_States_land_surveying));
[PLSS explained (GIS Geography)](https://gisgeography.com/public-land-survey-system-plss/);
[PLSS quarter sections (Township America)](https://townshipamerica.com/learn/plss/quarter-sections);
[Federal financing of suburbia, 1930s to now](https://shenandoahcountyva.us/DocumentCenter/View/425/1930s-To-Now-Federal-Financing-Of-Suburbia-PDF);
[Pennsylvania suburbs field guide: subdivision plans (PHMC)](https://www.phmc.state.pa.us/portal/communities/pa-suburbs/field-guide/subdivision.html);
[Exclusionary zoning (ASU Morrison Institute)](https://morrisoninstitute.asu.edu/sites/default/files/exclusionary_zoning_legal_barrier_to_affordable_housing.pdf);
[Minimum lot sizes over time (Philadelphia Fed WP 26-37)](https://www.philadelphiafed.org/-/media/FRBP/Assets/working-papers/2026/wp26-37.pdf);
[Shertzer: zoning history](https://www.allisonshertzer.com/static/ShertzerAllison_CookZone.pdf);
[Fed: trends in upsizing houses and shrinking lots](https://www.federalreserve.gov/econres/notes/feds-notes/trends-in-upsizing-houses-and-shrinking-lots-20171103.htm);
[Conzen's burgage cycle (urban morphology, KU)](https://kuscholarworks.ku.edu/bitstream/1808/33150/1/2020_Rashid_Urban%20Morphology%20and%20Historic%20Landscape%20Management.pdf);
[Plot-based morphology (Journal of Urban Morphology)](https://journal.urbanform.org/index.php/jum/article/view/4064).

### Building to lot: coverage over time

- **The national trend** (Fed note, 2017): the median new house grew from 1,600 to 2,400 sq ft between 1980 and
  2014, while the median lot shrank from 11,300 to 8,800 sq ft. The building-to-lot ratio rose from 0.14 to 0.27.
- **Zoning floor area ratios**: FAR limits for single-family zones run 0.3-0.6.
- **Lots change as towns age (Conzen's burgage cycle)**: plots first fill up (additions, rear buildings, then
  infill), then are amalgamated or cleared for renewal. The street layout outlasts the plots, and the plots outlast
  the buildings.
  - **For us**: an old district's lots carry more outbuildings, additions and odd subdivisions than a new one's.

## 2. What the measurements show (Wisconsin, 21 areas)

Medians per area. Width is along the street; depth is away from it. Coverage = building footprint / lot. Side gap =
the narrower side.

| Area | Place | Band | Width m | Depth m | Area m² | Coverage | Front setback m | Side gap m | Rear yard m | Alley | Corner | Outbuilding |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| prewar_alley_grid | Bay View, Milwaukee | streetcar | 12.1 | 39.3 | 370 | 0.39 | 4.1 | ~0 † | 17.9 | 78 % | 22 % | 67 % |
| streetcar_bungalow | Washington Heights, Milwaukee | streetcar | 12.4 | 36.5 | 425 | 0.43 | 3.8 | ~0 † | 13.0 | 19 % | 18 % | 82 % |
| rural_village | Plain | railroad | 24.3 | 40.5 | 784 | 0.22 | 5.6 | 2.5 | 18.2 | 43 % | 46 % | 51 % |
| small_town_main_street | Mineral Point | pioneer | 17.9 | 35.7 | 424 | 0.38 | 1.6 | 0.0 | 11.4 | 34 % | 34 % | (sparse OSM) |
| small_town_downtown | Baraboo | railroad | 18.0 | 40.2 | 490 | 0.36 | 2.0 | ~0 | 6.2 | 47 % | 24 % | 5 % |
| main_street_village | Wauwatosa | railroad | 37.2 | 42.2 | 953 | 0.33 | 3.9 | 2.4 | 9.7 | 32 % | 44 % | 42 % |
| planned_greenbelt_1938 | Greendale | interwar | 23.9 | 31.2 | 675 | 0.21 | 5.1 | 1.4 | 14.4 | 3 % | 31 % | 38 % |
| postwar_ranch | Westmorland, Madison | postwar | 23.5 | 41.7 | 899 | 0.20 | 8.9 | 2.4 | 17.5 | 2 % | 30 % | 9 % |
| arterial_strip | Kenosha | postwar | 17.8 | 38.2 | 663 | 0.23 | 8.3 | 1.3 | 17.3 | 22 % | 28 % | 72 % |
| mobile_home_park | Madison | postwar | (park parcels) | | 1,888 | 0.22 | 6.6 | | | | | |
| curvilinear_wooded | west Madison | suburban | 36.0 | 42.8 | 1,070 | 0.20 | 9.7 | 5.0 | 18.7 | 2 % | 35 % | 12 % |
| culdesac_1970s | Brookfield | suburban | 49.0 | 53.5 | 1,957 | 0.13 | 16.4 | 9.9 | 19.0 | 5 % | 29 % | 0 % |
| garden_apartments | west Madison | suburban | 29.7 | 41.7 | 1,020 | 0.17 | 12.4 | 2.9 | 16.6 | | | |
| mall_big_box | East Towne, Madison | suburban | 117 | 124 | 7,375 | 0.17 | 21.0 | 14.4 | 32.8 | (service drives) | | |
| newsub_1990s | Verona | late | 33.3 | 40.2 | 1,068 | 0.19 | 8.7 | 5.7 | 15.8 | 1 % | 31 % | 0 % |
| new_urbanist_1990s | Middleton Hills | late | 21.5 | 31.0 | 543 | 0.57 | 3.6 | 0.7 | 3.1 | 74 % | 34 % | 20 % |
| townhouse_condos | Fitchburg | late | (one common parcel, 280 x 152) | | 27,716 | 0.26 | | | | | | |
| newsub_edge | southwest Madison | current | 33.5 | 43.7 | 1,029 | 0.17 | 10.0 | 4.7 | 19.6 | 0 % | 33 % | 2 % |
| lakeshore_cottages | Fish Creek | streetcar | 19.4 | 30.7 | 520 | 0.18 | 11.8 | 3.2 | 15.1 | 11 % | 33 % | (sparse OSM) |
| industrial_valley | Menomonee Valley | railroad | 172 | 156 | 11,117 | 0.20 | (yards) | | | | | |
| farmland_plss | Town of Vienna | pioneer | 321 | 387 | 72,426 | 0.003 | 201 | 81 | 193 | 0 % | | |

† Parcel lines and OSM footprints are misregistered by about 1 m. On tight urban lots the least side gap reads ~0;
the true value is 0.6-1.5 m (a walkway each side). The renders show the houses clear of the lines.

- **Data gaps**: OSM building coverage is thin in Mineral Point and Fish Creek, which inflates the "vacant" counts
  there.
- **Corner shares**: about 25-45 % of lots are flagged as corners. Short blocks make corners common, and the detector
  is generous; treat it as an upper bound.

### What the numbers say

1. **Width tracks the era of the car, not the house's size.**
   - Streetcar lots are 12 m (40 ft) wide.
   - Greendale and the postwar ranch tracts are 24 m (78 ft).
   - 1970s Brookfield is 49 m (160 ft).
   - 1990s-2010s subdivisions come back down to 33 m (110 ft), as land prices rose and lots shrank (the Fed trend).
   - New Urbanism returns to 21.5 m with alleys.
2. **Depth barely moves**: 31-54 m everywhere in towns (100-180 ft). The block-depth convention (two lots back to
   back, 250-350 ft) is the oldest and most stable dimension.
3. **Coverage is highest where lots are narrow**: 0.39-0.43 in streetcar grids and 0.57 in New Urbanism (garages
   included). Postwar and suburban lots sit at 0.13-0.20.
4. **The front setback grows with the lot**: 4 m (streetcar) → 9 m (postwar) → 16 m (1970s) → 9-10 m (1990s+).
   Main streets sit at 0-2 m.
5. **The garage moves**:
   - In the alley grid, 67-82 % of lots have a rear outbuilding (the detached garage).
   - In Greendale it's 38 %; postwar 9 %; 1970s and new subdivisions 0-2 % (the garage is attached).
   - New Urbanism brings rear garages back (20 %, on the alley).
6. **Lot shape follows the street pattern**:
   - Grids give 72-90 % rectangular lots.
   - 1970s and later curvilinear streets and culs-de-sac give about a third irregular lots and 25-35 % pie or
     reverse-pie (wedge) lots, 10-20 % of each in the newer ones.
   - Mall and centre parcels are 20 % flag-shaped (pads with an access stem).

## 3. How lots are marked (boundaries)

From the aerials (all 21 areas) and the street-level photos (the token files' `bound_*` tokens).

| Setting | Front line | Side lines | Rear line | Why |
|---|---|---|---|---|
| **Prewar alley grid** | public sidewalk with a grass **terrace** and a regular **street-tree row**; sometimes a low iron or picket fence | mostly **unmarked** (lawns continuous) or a narrow walk; a few shrub rows or chain-link added later | the **garage row and alley**; tree canopy; chain-link or privacy fence in the back yard | The open-front-yard norm of the streetcar suburb; the alley handles service; fences went up later for dogs and kids (lot_contents/prewar_intown_lots.md) |
| **Small-town and village residential** | sidewalk (often without terrace) or none; mature street trees | unmarked or hedges and lilacs | garden, sheds, alley or field | Same, looser; more outbuildings and gardens |
| **Main street** | building wall at the sidewalk | party walls | rear yards and parking; often an alley | Fire-limit masonry blocks built to the lot line |
| **Postwar tract** | sidewalk and terrace (pre-1960s) or **none, a mown edge at the curb**; driveway | **lawn continuous** in front; rear yards split by **chain-link** or hedges; shrub rows at the house | rear fences (chain-link, later wood privacy), shrub and tree lines | Open lawns as the FHA and suburban ideal; privacy only behind the house |
| **1970s wooded curvilinear and cul-de-sac** | no sidewalk; **lawn to the street edge**, mailbox; driveway | lawns run together in front; **woodland and tree belts** behind | **woodland belt** (trees left at the rear and along drainage) | Large lots carved from woods; the trees at the rear become the boundary |
| **1990s-2010s subdivision** | sidewalk on one or both sides (codes again), young street trees; driveway to a front garage | **unmarked lawn**; some privacy fences behind | **wood or vinyl privacy fences** and young tree rows; stormwater ponds and open space at the edges | HOAs and codes: open fronts, fenced backs; detention ponds |
| **New Urbanist** | sidewalk with terrace and trees; picket fences and porches at shallow setbacks | narrow side yards, fences | the **alley with garages** | Deliberate return to the prewar pattern |
| **Mobile home park** | private lane, a carport or parking pad | small gaps, skirting; few fences | lane or park boundary fence and tree line | Leased pads; the park manager controls the edges |
| **Garden apartments and condos** | lawn to the street with a sidewalk | **none between buildings** (common lawn) | parking lots, garage rows; perimeter tree line or fence | One common parcel: no internal lot lines to mark |
| **Commercial strip and centre** | landscape strip, curb and parking edge; pylon sign | **curbed landscape islands**, pavement seams | service lane, dumpster enclosure, a buffer fence or tree line against houses | Zoning requires buffers and islands; otherwise the asphalt is continuous |
| **Industrial** | lawn setback with trees (park covenants), the sign | chain-link or nothing | **security fences** around yards; screening walls for outdoor storage | Security and screening rules |
| **Rural and farm** | mown edge or ditch at the road, the mailbox | **fence rows**: farm wire on posts, hedgerows, Osage-orange and walnut relics, windbreak rows | field edges, woodlots, creeks | Fences kept livestock in (before 1874's barbed wire, hedges did); trees grow up along fence lines that aren't ploughed |
| **Exurban acreage** | mown edge at the road | **mow line**: mown lawn against tall grass or field | the field edge or a windbreak | The lot is a mown island in farmland: mowing *is* the boundary |

### Why boundaries look like this (the general rules)

1. **Cues to care** (Nassauer, "Messy ecosystems, orderly frames", 1995): in North American culture a mown edge, a
   clipped hedge or a fence signals care and ownership.
   - The **mow line** (where one owner's mowing stops) is the most common boundary of all.
   - It also explains naturalistic yards that keep a mown frame.
2. **Front open, back closed**: almost every residential era keeps the front visually continuous (the street as a
   shared lawn) and marks the back.
   - Ordinances enforce this: front fences at most 3-4 ft, side and rear 6 ft, nothing over 3 ft in the corner
     vision triangle (20 ft from the corner).
3. **Grass changes**: a boundary often reads as two lawns mown at different times, heights or stripe directions, or
   watered differently.
   - At rural lots it's lawn against field grass.
   - Along terraces it's city-mown versus owner-mown.
4. **Trees grow where nobody mows**: fence lines, alleys, rear lot lines and drainage swales collect volunteer trees.
   - Old boundaries become tree lines (the windbreak, the hedgerow, the woodland belt).
5. **Hard edges where use changes**: parking against lawn (curb), residential against commercial (buffer fence or
   tree row), yard against street (sidewalk).

Sources: [Nassauer, "Messy ecosystems, orderly frames" (Deep Blue)](https://deepblue.lib.umich.edu/handle/2027.42/49351?show=full);
[Cues to care (Wild Ones)](https://wildones.org/cues-to-care-the-language-of-neighborly-landscaping/);
[Cues to care (UF IFAS)](https://edis.ifas.ufl.edu/publication/UW489/pdf);
[Yellow Springs OH fence rules (front 4 ft, rear 6 ft, vision triangle)](https://www.yellowsprings.gov/egov/documents/1682966139_16925.pdf);
[Euclid OH fence chapter](https://codelibrary.amlegal.com/codes/euclid/latest/euclid_oh/0-0-0-39891);
[Osage orange hedge fences (Wikipedia)](https://en.wikipedia.org/wiki/Osage_orange) (via lot_contents/expanded_trees_and_fences.md).

## 4. Lot tokens

These are in `tools/buildings/vocab.json` and documented in TOKENS.md. `lot_sample.py` writes them per lot; photo annotations
add the boundary tokens.

| Family | Values | Derived from |
|---|---|---|
| `lot_w` | very_narrow (<9 m), narrow (<14), standard (<22), wide (<35), very_wide (<70), acreage | measured width along the street |
| `lot_depth` | shallow (<25), standard (<40), deep (<55), very_deep (<90), acreage | measured depth |
| `lot_shape` | rect, pie (rear 1.6x front), reverse_pie, flag (narrow stem), irregular, through, l_shape | front and rear width at 12 % and 88 % depth, rectangularity |
| `lot_access` | street, alley, shared_drive, private_road, service_drive | alley within 6 m of the lot |
| `lot_corner` | yes, no | a second street crossing at >45° along another side |
| `lot_coverage` | vacant, sparse, low, medium, high, full | footprint / lot area |
| `setback`, `side_gap`, `rear_yard` | relative classes | the principal building's position in the lot frame |
| `outbuilding` | none, rear, side, front | the other buildings on the lot |
| `lot_tenure` | fee_simple, condo_common, park_lease, outparcel, aliquot_farm, institutional | parcel attributes and context |
| `bound_front`, `bound_side`, `bound_rear` | 30 marker values: lawn_continuous, mow_line, sidewalk_terrace, hedge, tree_line, woodland_belt, windbreak_row, fence_*, wall_retaining, garage_row, alley, parking_edge, landscape_island, field_edge, ... | annotation (photos, aerials) |

## 5. Rules for the generator

1. **Plat by era, not by house**: a band's block and lot grid comes first (urban_layout).
   - **Lot width by band**: 10-13 m streetcar, 15-18 m town, 21-25 m postwar, 30-50 m 1970s, 30-35 m since 1990,
     20-22 m New Urbanist, 0.4-2 ha exurban.
   - **Depth**: 31-45 m in towns.
   - **Rural**: aliquot farms on the mile grid.
2. **Shape follows street geometry**: rectangles on grids; wedges on curves and bulbs (Vanegas-style straight-skeleton
   splits keep frontage); flags behind pads and on deep rural parcels.
3. **The building fits the lot by era**:
   - coverage 0.35-0.45 (prewar), 0.18-0.22 (postwar), 0.13-0.20 (suburban), 0.5+ (New Urbanist);
   - setback from the band's median ±20 %, the same along a block face (03_compatibility);
   - side gaps at least the code minimum (0.9-1.5 m prewar, 1.5-3 m postwar, 3-10 m suburban).
4. **Outbuildings by band**: rear garage on the alley (prewar, about 70 %), side or rear detached garage (small towns,
   about 50 %), none (attached garage, 1960s+), alley garage (New Urbanist).
5. **Boundaries by setting** (§3):
   - fronts open;
   - sides open in front and fenced or hedged behind with era-appropriate fences;
   - rear lines become garages (alley), fences, woodland belts or field edges;
   - boundaries that have been unmown for 30+ years grow tree lines.
6. **Common parcels have no internal lot lines** (condos, apartments, mobile home parks, centres): place buildings by
   the site plan (07) and draw no fences between units.
7. **Change over time** (urban_layout/03, Conzen):
   - Older districts gain rear additions, sheds, garages, fences, paved-over yards and the odd lot split.
   - Declining districts gain vacant lots (side-yard expansions, community gardens).
   - Gentrifying districts gain privacy fences and replaced garages.
