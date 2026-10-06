# Zoning: how land is divided by rule (2026-10-05)

Collected for the settlement generator (README.md). The question here: what rules decide what may be built where,
and how those rules change the shape of a town.

## Euclidean (use) zoning -- the American default

- **New York 1916**: the first comprehensive zoning ordinance, a response to height, light, air and conflicting uses.
- **Village of Euclid, Ohio, 1922**: divided the village into six cumulative use districts.
  - U-1 is single-family only, U-2 adds two-family, U-3 adds multi-family, and so on up to U-6 (industry).
  - *Cumulative* means a "higher" use may go in any "lower" district: houses may stand in an industrial zone, but
    not the other way round.
- **Euclid v. Ambler Realty, 1926**: the Supreme Court upheld it. Zoning needs only to bear a reasonable relation to
  public health, safety or welfare, and that gave towns broad discretion.
- It is still the most common form of land-use control in the US.
- **Shift after the war**: zoning moved from cumulative to *exclusive* districts (each use only in its own zone).
  This separation of uses, applied on a large scale, is the planning half of sprawl (05_suburban_sprawl.md).

Sources: [Ambler Realty v. Village of Euclid (Quimbee)](https://www.quimbee.com/cases/ambler-realty-co-v-village-of-euclid-ohio-297-f-307-1924);
[City of Euclid: historic documents](https://www.cityofeuclid.gov/euclidean-zoning---historic-documents);
[Vital City: floating zoning](https://www.vitalcitynyc.org/articles/the-promise-of-floating-zoning);
[Zoning classifications, setbacks, envelopes](https://open-exam-prep.com/study-guides/are-pa/ch07-zoning-entitlements/zoning-setbacks-height).

### The parts of a zoning code (what a generator must decide per lot)

| Control | What it sets | Typical small-town range (US) |
|---|---|---|
| Permitted use | Which uses go in the district | R-1 single family ... C-2 general commercial ... M-1 light industry |
| Minimum lot area and width | The grain of the district | R-1: 7,500-10,000 sq ft, 60-80 ft wide; older R-2: 5,000 sq ft, 40-50 ft |
| Setbacks (front, side, rear) | Where on the lot the building sits | R-1 front 25-35 ft, side 5-10 ft, rear 25 ft; downtown C: 0 |
| Height | Storeys and feet | 2.5 storeys / 35 ft residential; 3-5 storeys downtown |
| Lot coverage, floor area ratio | How much is built | 30-40 % coverage residential; FAR 1-3 downtown |
| Parking minimum | Spaces per unit or per 1,000 sq ft | 2 per house; 3-5 per 1,000 sq ft retail (the land-eater: below) |

The setback and parking columns are what make a 1960s strip look different from a 1910 Main Street, more than the
use column does.

## Form-based codes and the Transect

- **Form-based codes** regulate the building's form and its relation to the street (frontage, height, placement,
  parking location) rather than its use.
- **The SmartCode** (Duany Plater-Zyberk) arranges every district along the *rural-to-urban Transect*:
  - **T1 Natural**: no building; parks and greenways.
  - **T2 Rural**: farmland and scattered buildings, 1-2 storeys, variable setbacks.
  - **T3 Sub-Urban**: detached houses on lawns, large and variable front and side setbacks, 1-2 storeys (some 3).
  - **T4 General Urban**: mixed houses, rowhouses and small apartments; shallow setbacks; 2-3 storeys.
  - **T5 Urban Centre**: shopfronts and attached buildings at the sidewalk; 2-5 storeys.
  - **T6 Urban Core**: the downtown of a city; tallest, zero setback.
  - Also **SD**: special districts (industry, campus, big-box).
- **The rule along it**: setbacks shrink and heights rise from T1 to T6, while greenery shrinks. Lot widths narrow,
  blocks shorten, and parking moves from the front to the rear, then into structures.
- **For us**: the Transect is a *single continuous parameter* from which a whole bundle of lot and street settings
  can be derived. That is the "few high-level knobs" design our procgen principles call for.

Sources: [SmartCode (Wikipedia)](https://en.wikipedia.org/wiki/SmartCode);
[Form-based codes (U. Idaho)](https://webpages.uidaho.edu/larc453/pdf/form_based_codes.pdf);
[Skaneateles transect zone descriptions](https://www.townofskaneateles.gov/assets/Transect-Zone-Descriptions-Final.pdf);
[Tuxedo revised SmartCode](https://www.tuxedogov.org/sites/g/files/vyhlif5996/f/uploads/2023-06-26_revised_smartcode.pdf).

## Missing-middle housing (what sits between the house and the apartment block)

- **Opticos's list (Parolek)**:
  - duplex (2 units); triplex or fourplex (3-4);
  - cottage court (3-10); multiplex medium (5-10) and large (6-18);
  - courtyard building medium (6-16) and large (16-28); townhouse runs of 3-8.
- **Scale**: mostly 2-2.5 storeys, house-scaled. Most have 4-8 units a building.
- **On a 50 x 100 ft lot**: a side-by-side duplex gives 17 dwellings an acre, a fourplex 32.
- **Why it matters**: pre-1940 neighbourhoods are full of these types, and post-1940 R-1 zoning made them illegal.
  A generator that dates its districts should place them in the older T3-T4 fabric and leave them out of postwar
  subdivisions.

Sources: [Utah Missing Middle toolkit](https://luau.utah.gov/wp-content/uploads/UMH_MMH-Toolkit_NeighborhoodTypes_Central.pdf);
[SPUR: reimagining density (Parolek)](https://www.spur.org/sites/default/files/2016-03/2016.05.17%20Reimagining%20Density%20and%20Housing%20Diversity%20(Karen%20Parolek).pdf);
[Squamish: the missing middle](https://squamish.ca/business-and-development/home-land-and-property-development/community-planning-blog/missing-middle/).

## Parking requirements (Shoup)

- **The claim**: minimum parking requirements are the hidden zoning rule that most shapes car-era towns.
- **Cost**: they raise a shopping centre's construction cost by up to 67 % with structured parking and 93 % with
  underground parking. As an impact fee they can exceed all other impact fees combined by more than 10x.
- **Land**: typical retail minimums of 3-5 spaces per 1,000 sq ft mean the car park covers more ground than the
  store, which is the look of the 1960s-80s strip.
- **Reform**: proposed caps are about 1 space per dwelling or 2 per 1,000 sq ft commercial.
- **For us**: the car park's share of each commercial lot is a period marker. Pre-1930 retail has none (street
  parking); postwar retail sits behind a lot as large as the building or larger.
  - SSC note: our vehicles are electric and the game year is 2752, but the towns are styled on 1970s Great Lakes
    towns (the bible), so the period rules apply by founding era.

Sources: [Shoup, The High Cost of Free Parking (APA)](https://planning.org/knowledgebase/resource/9127817);
[High cost of minimum parking requirements](https://emeraldinsight.com/insight/content/doi/10.1108/S2044-994120140000005011);
[NJ TOD summary](https://www.njtod.org/?p=24708).

## Incrementalism (Strong Towns) -- how a town actually gets built

- **The traditional pattern**: small lots, little or no front setback on commercial streets, and each place
  *thickening one increment at a time*.
  - A house becomes a duplex, a duplex becomes a small apartment building, and a corner lot becomes a shop.
- **What zoning freezes**: in the postwar pattern, zoning sets each lot's final form at subdivision time.
- **For us**: this is the time dimension a generator needs. A lot has a *founding form* and later *increments*,
  and the mix of the two tells a district's age (03_neighbourhood_change.md).

Sources: [Strong Towns: what is traditional development](https://strongtowns.org/journal/2019/6/14/traditional-development);
[What does incrementalism actually mean?](https://strongtowns.org/journal/2018/9/5/incrementalism);
[The power of growing incrementally](https://archive.strongtowns.org/journal/2017/6/12/the-power-of-growing-incrementally).
