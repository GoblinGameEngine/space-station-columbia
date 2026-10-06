# Strip malls, open-air centres and industrial parks: why they are laid out as they are (2026-10-05)

The user, 2026-10-05: "analyze strip malls, open air shopping malls, and industrial parks; we will be needing lots of
all. Find out why they are laid out the way they are, what purposes the layouts serve, which sorts of business would
you find there and why. Add all of this to the map generation engine."

- **Engine**: `tools/settlegen/centers.py` (generators), previewed by `tools/settlegen/preview_centers.py`.
- **Real examples measured**: `tools/buildings/center_sample.py`, results in `centers/` (§6).

## 1. The family of centres (ICSC classification, January 2017)

| Type | Concept | Typical GLA (sq ft) | Acres | Anchors | Anchor share of GLA | Typical anchors | Trade area | US count |
|---|---|---|---|---|---|---|---|---|
| **Strip / convenience** | A row of stores, parking in front, maybe a canopy; straight, L or U | < 30,000 | < 3 | none, or a convenience store | — | convenience store | < 1 mile | 68,936 |
| **Neighbourhood centre** | Convenience: daily needs | 30,000-125,000 | 3-5 | 1+ | 30-50 % | **supermarket** | 3 miles | 32,588 |
| **Community centre** ("large neighbourhood") | General merchandise plus convenience; strip, L or U | 125,000-400,000 | 10-40 | 2+ | 40-60 % | discount store, supermarket, drug, large specialty (toys, books, electronics, home, sporting goods) | 3-6 miles | 9,776 |
| **Power centre** | Category-dominant anchors and few small tenants | 250,000-600,000 | 25-80 | 3+ | **70-90 %** | category killers: home improvement, discount department, warehouse club, off-price | 5-10 miles | 2,258 |
| **Lifestyle centre** | Upscale national specialty stores with dining and entertainment, **outdoors** | 150,000-500,000 | 10-40 | 0-2 | 0-50 % | large-format upscale specialty | 8-12 miles | 491 |
| **Factory outlet** | Brand-name goods at a discount | 50,000-400,000 | 10-50 | — | — | manufacturers' outlets | **25-75 miles** | 367 |
| **Regional mall** | Enclosed, inward-facing; parking all round | 400,000-800,000 | 40-100 | 2+ | 50-70 % | department stores | 5-15 miles | 600 |
| **Super-regional mall** | Larger regional | 800,000+ | 60-120 | 3+ | 50-70 % | department stores | 5-25 miles | 620 |
| **Theme / festival** | Leisure and tourist retail, often in old buildings | 80,000-250,000 | 5-20 | — | — | restaurants, entertainment | 25-75 miles | 159 |

**Reading the table**: 87 % of US centres are strips and neighbourhood centres. That's the ratio our towns need: many
small strips, a supermarket centre per 3-mile catchment, one community or power centre per town of 15-30k, and a mall
or lifestyle centre only at regional scale (urban_layout/02 §Christaller).

Sources: [ICSC US shopping-centre classification (PDF)](https://www.icsc.com/uploads/research/general/US_CENTER_CLASSIFICATION.pdf);
[DeLisle: US classifications](https://www.jrdelisle.com/research/US%20Classifications.pdf);
[Neptis: shopping centres](https://neptis.org/publications/chapters/shopping-centres);
[ICSC Canadian definitions](https://www.icsc.com/uploads/research/general/Canadian-Shopping-Centre-Definitions.pdf).

## 2. Why a strip centre looks like a strip centre

Each element of the layout answers a specific pressure:

| Element | What it is | Why |
|---|---|---|
| **The store row faces the road across its parking** | Building at the back of the lot, parking between it and the arterial | **Visibility from the moving car** (Venturi): the driver must see the whole row and its signs before the turn. **Parking minimums** (3-5 spaces per 1,000 sq ft; Shoup) fill the front. Parking in front also *proves* to the passing driver that it's easy to stop |
| **A corner site at a signalled intersection** | Two arterials meeting | Access from both directions and both roads; the traffic counts that retailers screen for ("retail grows where two main roads meet") |
| **Straight, L or U** | The row bends round the corner or wraps the lot | Fits the lot while keeping every front visible from the entry; the L puts the anchor in the corner where both roads see it |
| **Anchor at the end or corner** (the "dumbbell" when there are two) | Supermarket or drugstore at one end, second anchor at the other | **Anchors generate the trips; in-line shops live on the walk between.** Parking aisles run perpendicular to the anchor's door so cars and people flow toward it. Anchors pay low rent per sq ft; in-line tenants pay the highest |
| **In-line shops 60-100 ft deep, 20-30 ft wide bays** | The thin row between anchors | A small tenant needs frontage more than depth; the bay module (about 24 ft) matches the structural grid and lets tenants combine bays |
| **Anchors 150-250 ft deep** | A deep box | Supermarkets and discount stores need their whole selling floor plus stockroom and receiving |
| **End caps** | The bays at each end of the row | Visible from the side street too: the most valuable in-line bays (banks, mobile phone shops, quick restaurants with patios) |
| **A canopy or arcade** | A covered walk along the fronts | Weather (Great Lakes winters), a continuous sign band, a unified look |
| **A service lane behind** | Truck access, dumpsters, loading at the rear | Keeps delivery trucks out of customer parking; the rear wall is blank |
| **Pads and outparcels** | Freestanding small buildings (about 15,000 sq ft lots) at the road edge of the parking field | The most visible ground goes to **drive-through** uses (fast food, banks, pharmacies, coffee) and to ground-leased restaurants; the landlord earns rent on land that would otherwise be parking. Pads also screen the parking from the road |
| **Pylon or monument sign at the entrance** | One tall sign listing the tenants | The in-line shops are too far back to be read from the road (Venturi's decorated shed) |
| **Landscape islands, perimeter strip, storm pond** | Curbed islands every 10-15 stalls; a buffer strip; a detention pond | Modern zoning (tree counts, impervious-surface limits) and stormwater rules; older centres have bare asphalt |
| **A curb cut on each road, aligned with the signal** | Entry drives | Access management: limited cuts, the main one at the traffic light |

Sources: [ABAG: why retailers make the location decisions they do](https://abag.ca.gov/sites/default/files/why_retailers_make_the_location_decisions_they_do.pdf);
[How to design a mall (anchors, dumbbell)](https://archgyan.com/how-to-design-a-mall/);
[TestFit: anchored parking and drive-throughs](https://www.testfit.io/blog/testfit-5-12-optimize-retail-sites-with-anchored-parking-custom-drive-thrus);
[VTS: standard retail spaces (pads, end caps)](https://reports.vts.com/?p=218);
[Tenant mix (fnrp)](https://fnrpusa.com/blog/understanding-the-importance-of-a-shopping-centers-tenant-mix/);
[Anchor tenants (Ariadne)](https://www.ariadne.inc/resources/blogs/anchor-tenants);
[Junior anchors (Ariadne)](https://www.ariadne.inc/resources/blogs/junior-anchor-tenant/);
[Tenant mix theory (HKU thesis)](https://repository.hku.hk/handle/10722/194919);
[Tenant mix (DUT)](https://www.dut.ac.za/wp-content/uploads/2019/06/Tenant-Mix.pdf);
[TCLF: strip malls and shopping centres](https://www.tclf.org/category/designed-landscape-types/strip-malls-and-shopping-centers);
[Cleveland Park 1931: the first drive-in strip (GGWash)](https://ggwash.org/view/87521/back-in-1931-this-parking-lot-in-cleveland-park-changed-how-washington-shopped).

### Who rents there, and why

- **The principle**: the mix is a system of trip generators and trip catchers (cumulative attraction; central place
  thresholds, urban_layout/02).
  - **Anchors** make trips: weekly needs and destination goods.
  - **Junior anchors** extend the trip.
  - **In-line tenants** catch the passing shopper or need cheap visible space.
  - **Pads** catch the driver who never parks.

| Centre | Anchor | Typical in-line and pad tenants | Why they cluster |
|---|---|---|---|
| Strip / convenience | none, or a convenience store | nail salon, dry cleaner, pizza or Chinese takeout, tax preparer, mobile phone, vape, dollar store, laundromat, insurance agent, video rental (period), liquor or party store | Cheap rent, frequent short trips, parking at the door; services that need visibility but not foot traffic |
| Neighbourhood | supermarket (35-60k sq ft), sometimes a drugstore | bank, pharmacy, hair salon, dentist, quick food, video or rental, hardware, pet supplies, fitness | **The weekly grocery trip** is the base; everything else catches it |
| Community | discount department store (Kmart, Meijer-type), supermarket, drug | shoe store, apparel chain, books, crafts, electronics, sit-down chain restaurant pad, auto parts | A bigger catchment for general merchandise; apparel and household follow the discount anchor |
| Power | 3+ category killers (home improvement, electronics, office supply, sporting goods, pet, books, bed-and-bath, warehouse club) | very few small tenants; restaurant and bank pads | Destination shopping: one trip per category; anchors need their own parking at their own door; little walking between |
| Lifestyle | none or a cinema, a bookstore | apparel and specialty chains, cafés, restaurants with patios, cinema, fitness, apartments or offices above (newer ones) | **Dwell time**: the walkable "main street" makes shopping a leisure trip; restaurants and cinema keep it alive at night |
| Outlet | — | brand outlets | Far from the full-price stores they would compete with (the 25-75 mile radius) |

### Open-air "main street" layout (lifestyle centres, the modern town centre)

- **Lineage**: J.C. Nichols's **Country Club Plaza** (Kansas City, 1922-23: the first car-oriented planned centre,
  with shops on streets and parking in lots and garages behind). Victor Gruen's **Northland Center** (Southfield,
  Michigan, 1954) was the largest in the US when it opened, an open-air pedestrian mall of separate buildings around
  courts in a sea of parking. **Shopper's World** (Framingham, 1951) had a landscaped open mall like a town common.
- **The 1990s lifestyle centre** returns to the street.
  - **Shops face a pedestrian street (sometimes with slow traffic and angle parking)**, two storeys, with varied
    "historic" facades over standard boxes.
  - **Parking in lots or decks behind** the shop rows, reached through mid-block passages.
  - A **square or green** at the centre with a fountain, and a cinema or bookstore as the evening anchor.
  - Restaurant pads at the corners.
- **Why**:
  - The enclosed mall was losing to discounters and power centres.
  - An outdoor street sells *experience* (the Jacobs street, the Lynch node) and keeps shoppers longer.
  - Newer ones add apartments over shops, becoming a mixed-use "town centre". Bayshore in Glendale, Wisconsin, a
    1950s mall rebuilt as a town centre, is measured below.

Sources: [SAH Archipedia: shopping centres](https://sah.org/about-sah/news/news-detail/2022/01/05/sah-archipedia-highlights-shopping-centers);
[Northland Center (Wikipedia)](https://en.wikipedia.org/wiki/Northland_Center);
[Victor Gruen (Wikipedia)](https://en.wikipedia.org/wiki/Victor_Gruen);
[Gruen (Encyclopedia of Detroit)](https://detroithistorical.org/learn/encyclopedia-of-detroit/gruen-victor);
[Shopper's World (Wikipedia)](https://en.wikipedia.org/wiki/Shopper%27s_World);
[Shopper's World and the regional centre (SCA)](https://sca-roadside.org/shoppers-world-and-the-regional-shopping-center-in-greater-boston/);
[Lifestyle centres originated in the US (Asia Research News)](https://www.asiaresearchnews.com/node/7710);
[Buildings of the decades: the shopping centre's future](https://www.buildings.com/industry-news/article/10193550/buildings-of-the-decades-the-shopping-centers-future);
[Dead and dying retail: Northland](https://www.deadanddyingretail.com/2015/03/northland-center-in-southfield-michigan.html).

## 3. Industrial parks

### Where they come from

- **The planned industrial district**: Chicago's **Central Manufacturing District** (1905, 265 acres, the first in the
  US) and the **Clearing Industrial District** (1909).
  - **The idea**: land, rail sidings, utilities and shared services are laid out in advance and sold or leased to
    manufacturers.
  - Clearing's plan used **40-acre superblocks each with a rail lead**, next to the Clearing freight yards. It had 18
    industries in 1915 and more than 90 by 1928.
- **After 1945**: the **suburban industrial park** follows trucks and interstates, not rail.
  - Curving or loop roads, large lots, and protective covenants: setbacks, landscaping, no outdoor storage, masonry
    fronts.
  - One-storey buildings, because forklifts and continuous assembly lines want a single floor.
  - Manufacturers left the old multi-storey loft districts (urban_layout/03: the rent gap they left behind).
- **Since about 2000**: **logistics parks** of big distribution boxes at interchanges and **flex / business parks**
  of small units.

Sources: [Clearing, Chicago (Wikipedia)](https://en.wikipedia.org/wiki/Clearing,_Chicago);
[Encyclopedia of Chicago: Clearing](https://encyclopedia.chicagohistory.org/pages/296.html);
[Encyclopedia of Chicago: Central Manufacturing District](https://encyclopedia.chicagohistory.org/pages/785.html);
[WBEZ: the nation's first industrial park](https://www.wbez.org/stories/whats-that-building-chicagos-central-manufacturing-district/3bbcba2b-6c2f-4e43-8c1e-7f5ee4647f00);
[ASU: industrial parks (history and research)](https://gradstudents.wpcarey.asu.edu/sites/default/files/parks.pdf).

### The building types (who is there, what the building looks like)

| Type | Office share | Clear height | Depth | Docks | Typical occupants | Why it looks the way it does |
|---|---|---|---|---|---|---|
| **Heavy manufacturing** | 0-5 % | 20-40 ft (cranes) | irregular, additions | some docks, rail | foundries, stamping, paper, food processing, chemicals | Process-driven: tall bays, stacks, tanks, outdoor yards; grows by additions |
| **Light industrial / assembly** | under 10 % | 18-24 ft | 100-200 ft | a few docks, drive-in doors | machine shops, fabrication, printing, small assembly, packaging | A one-storey box sized to the line; an office at the front |
| **Warehouse / regional distribution** | about 5-15 % | 24-32 ft | 150-300 ft | rear-load, about 1 door per 10,000 sq ft | wholesale distributors, 3PLs, building supply | Storage is vertical: clear height sets racking; docks on one long side |
| **Bulk distribution / fulfilment** | under 5 % | 32-40 ft+ | 400-600 ft | **cross-dock**: both long sides | big-box retailers' DCs, e-commerce | Inbound on one side, outbound on the other; a 185-200 ft truck court each side with trailer stalls |
| **Truck terminal** | small | low | long and narrow (60-100 ft) | doors along both sides | LTL carriers | Freight moves truck to truck; little storage |
| **Flex / R&D** | **30-100 %** | 14-20 ft | 60-120 ft | grade-level doors, a few docks | contractors, labs, small tech, showrooms | Office fronts with glass, overhead doors behind; looks like an office from the street |
| **Contractor / service yard** | small | low | small building | drive-in doors | landscapers, excavators, roofing, equipment rental | A small shop building with a large fenced outdoor yard |
| **Self-storage** | none | — | long thin rows | roll-up doors on every unit | storage | Rows of 10-30 ft deep units with drive aisles between; fenced, gated |

Sources: [NAIOP terms and definitions (PDF)](https://www.naiop.org/globalassets/research-and-publications/report/terms-and-definitions-/researchreportnaiop-terms-and-definitions-2012.pdf);
[Prologis: industrial building types](https://www.prologis.com/about/resources/industrial-real-estate-building-types);
[Crexi: industrial building types explained](https://www.crexi.com/insights/the-different-industrial-building-types-explained);
[Link Logistics: clear height](https://www.linklogistics.com/news-insights/industrial-real-estate-101/what-is-clear-height-a-guide-to-warehouse-ceilings-and-vertical-space/);
[Bulk warehouse (RETS glossary)](https://rets.ai/glossary/bulk-warehouse);
[Truck court (RETS glossary)](https://rets.ai/glossary/truck-court);
[Rear-load (Cove glossary)](https://cove.is/glossary/rear-load);
[Front-load (Cove glossary)](https://cove.is/glossary/front-load);
[Industrial and logistics facilities: clear heights, intermodal hubs (CCIM prep)](https://open-exam-prep.com/study-guides/ccim/ch8-commercial-sectors/industrial-market-analysis);
[NAI: logistics terminology](https://www.naiglobal.com/news/cre-terms-11-logistics-terminology/).

### Why an industrial park is laid out as it is

| Element | Why |
|---|---|
| **Next to the interstate interchange, rail or water** | Freight cost dominates. Since the 1950s that means the truck, so parks cluster within a few minutes of an interchange. Older districts line the rail and the river (our map's rail line) |
| **One collector road looping through, few entrances** | Keeps trucks off residential streets; a loop lets 53 ft trailers circulate without turning round; culs-de-sac end in large bulbs for truck turning |
| **Large rectangular lots (2-40 acres), deep from the road** | The building's depth plus a truck court plus car parking. Lots are cut to fit the building type, not a grid |
| **Building parallel to the road, offices and car parking in front, docks behind or at the side** | The front is the "address" (glass office, landscaping, the company sign); trucks stay out of view. Rear-load is the default; cross-dock for big DCs |
| **Truck courts 120-135 ft (older), 185-200 ft (bulk)** | Sized by the largest legal tractor-trailer's turning: a truck must back into a dock in one move with a trailer row behind it |
| **Trailer parking stalls** | Drop-and-hook operations park empty and full trailers away from the doors |
| **Coverage about 35-45 % (FAR 0.3-0.5)** | Truck courts, parking, setbacks and stormwater take the rest |
| **Front setbacks 30-50 ft with lawn and trees; side and rear smaller; screening of outdoor storage (6 ft opaque)** | Covenants and zoning (the industrial-park image), and buffers next to housing |
| **Stormwater ponds** | Roofs and paving shed huge runoff; detention ponds are standard after the 1970s |
| **Utilities sized up front** | Heavy power, water and sewer brought in at the park's creation (the point of a *planned* district) |

Sources: [Industrial zone standards (Anaheim)](https://www.anaheim.net/DocumentCenter/View/1192/I---Zone-Development-Standards);
[Hopkinton MA industrial zoning](https://www.zoneomics.com/code/hopkinton-MA/chapter_9);
[Lakeport industrial zone](https://codepublishing.com/CA/Lakeport/html/Lakeport17/Lakeport1713.html);
[Edmonton medium industrial zone](https://zoningbylaw.edmonton.ca/part-3-special-area-zones/ellerslie-industrial-special-area/3182-eim-ellerslie-medium-industrial-zone);
[Truck court sizing (RETS)](https://rets.ai/glossary/truck-court).

## 4. Where they go in a town (siting rules for the engine)

- **Strip centres**:
  - at arterial-arterial and arterial-collector corners;
  - along the strip at about 1/4-1/2 mile spacing in car-era bands (urban_layout/05);
  - tiny convenience strips at neighbourhood edges.
- **Neighbourhood centre**: one per about 3-mile catchment, or about 8-12k people (the supermarket threshold), at the
  edge of a neighbourhood unit (Perry, urban_layout/02).
- **Community or power centre**: at the town's main arterial or the highway, toward the growth side; one per town of
  15-30k+.
- **Lifestyle centre**: regional, near the interstate and the affluent sector (Hoyt), or replacing a dead mall.
- **Industrial**:
  - the old district along the rail and river, inside the town;
  - a planned park at the interchange or along the rail spur on the edge opposite the affluent sector (Hoyt: industry
    and working-class housing share a wedge; prevailing winds put it downwind);
  - flex and business parks near the interchange or the community centre.
- **Proportions (a 10k-person town)**: about 3-6 strips, 1 supermarket centre, 1 small community centre or a
  discount-anchored strip, 1 industrial park of 50-150 acres, and an old rail-side industrial strip.

## 5. The generators (tools/settlegen/centers.py)

Every generator is a pure function of a **site** (a rectangle in the town's u/v frame, its road frontages), a **type**
and a seeded RNG. Each returns:

- buildings with role and tenant category;
- parking fields with aisles;
- drives and curb cuts, the service lane, loading and truck courts;
- landscape and ponds, signs.

`place(town, plan)` writes the plan into a map_expanded `Town` (`bld`, `area`, `street`). Dimensions and proportions
come from §2-§3, and the measured examples in §6 check them.

- `strip_center(site, kind="convenience|neighborhood|community|power")`: a row (straight, L or U by frontage) with
  anchors at the ends, in-line bays of 20-30 ft x 60-100 ft, pads at the road edge, a parking field sized to
  4-5 per 1,000 sq ft, a rear service lane, entry drives aligned to the frontage, a pylon sign.
- `lifestyle_center(site)`: a pedestrian street of two-storey shop blocks, a central green, a cinema or bookstore
  anchor, parking behind in lots or a deck, restaurant pads at the corners.
- `industrial_park(site, era="rail|postwar|logistics")`: a loop collector, lots by building type mix (manufacturing,
  warehouse, distribution, flex, contractor yard, self-storage), each building oriented with its office front to the
  road and its truck court behind, trailer stalls, employee parking in front, a pond, a rail spur for the "rail" era.
- `tenants(plan, rng)`: fills roles with business categories from §2's mix (never brand names: the catalog rule).

## 6. Measured examples

(`tools/buildings/center_sample.py`: OSM buildings, parking and tenant tags; NAIP render. See `centers/*.json`.)

Ten real places, measured 2026-10-05:

- **Caveats**:
  - Each sample box also catches neighbouring houses, which inflates the "pad" counts (any building of 1,500-3,000
    sq ft).
  - OSM maps industrial parking poorly, so the industrial parking ratios read 0.
  - Depths and tenant tags are the reliable figures.

| Sample | Type | Anchor depth (ft) | Junior depth | In-line depth | Stalls per 1,000 sq ft | What the tenant tags show |
|---|---|---|---|---|---|---|
| Silver Spring Shopping Center, Milwaukee | neighbourhood | 185 | 141 | 45 | (under-mapped) | fast food, variety, auto parts |
| Bayshore, Glendale | lifestyle (a rebuilt mall) | 223 | 143 | 65 | (decks) | apparel 14, restaurants 7, fast food 7, optician 4, beauty 4, shoes 4, bank 3, department stores 2, jewellery 2 |
| Greenway Station, Middleton | lifestyle | 231 | 132 | 75 | 3.6 | apparel 9, restaurants 6, fast food 5, beauty 3, home decor 2, sports 2, cafe, wine, bank |
| The Corners of Brookfield | lifestyle | 253 | 126 | 85 | 4.1 | apparel 7, restaurants 5, beauty 2, a cinema, a supermarket, furniture, fitness |
| Hilldale, Madison | open-air community centre with apartments | 262 | 121 | 70 | (mixed) | apparel 13, restaurants 8, cafes 3, shoes 3, pharmacy, bank, department stores 2, fitness 2, books |
| West Towne, Madison | regional mall + power centres | 252 | 133 | 74 | **4.5** | fast food 17, apparel 11, restaurants 9, jewellery 7, cosmetics 5, sports 4, department stores 4 |
| New Berlin Industrial Park | postwar industrial park | 231 | 120 | 76 | — | (few tags) |
| Germantown Gateway | modern industrial park | 259 | — | 44 | — | — |
| South Branch, Oak Creek | industrial park | 210 | 128 | 60 | — | fuel 3, storage rental, convenience (the services that serve a park's workers and trucks) |
| Sun Prairie Business Park | logistics / business park | **375** | 121 | 78 | — | — |

**What the measurements confirm**:

- **Anchors are 185-260 ft deep, juniors 120-145, in-line shops 45-85.** The generator's ranges (anchors 180-320,
  juniors 90-160, in-line 55-100 ft) sit on them.
- **Parking is 4-4.5 stalls per 1,000 sq ft** where it's mapped. Lifestyle centres run lower (3.6-4.1), because they
  use decks and on-street spaces.
- **Lifestyle and open-air centres are apparel + restaurants + personal care.** Power and regional centres add a
  ring of **fast food** on the outparcels (17 at West Towne).
- **Industrial buildings are 210-260 ft deep** (64-79 m: the generator's 40-85 m light-industrial and warehouse
  range). Modern distribution boxes reach 375 ft (Sun Prairie; the generator's bulk range is 100-170 m).
- **Industrial parks host a ring of worker and truck services**: fuel, convenience, storage. That's a small "service
  pad" cluster at the park's entrance (added to the plan as future work).

**What the aerials add** (`reference/centers/*.png`):

- **The regional centre's ring road**: West Towne's mall sits in a parking field circled by a private ring road.
  Outparcels (restaurants, banks, auto service) line the ring on the arterial side, and power-centre boxes sit across
  the ring with their own fields. The ring separates through traffic from parking-aisle traffic and gives every
  outparcel two frontages. *Next generator*: `regional_center(site)` = mall box + ring + outparcels.
- **The postwar industrial park's grain** (New Berlin):
  - Roads every 150-250 m, many small buildings of 20-60k sq ft on 50-120 m lots, and a drainage greenway through
    the middle.
  - The generator's postwar spacing and lot sizes were tightened to match (`centers.py`: spine pitch 230 m, lots
    55-120 m).
