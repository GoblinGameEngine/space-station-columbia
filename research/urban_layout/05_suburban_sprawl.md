# Suburban sprawl: what it is, how it was built, how to measure it (2026-10-05)

## Measuring it (Ewing and Hamidi)

- **The index**: a composite of up to 21 variables in four dimensions. It covers 233 metro areas, 995 counties and
  64,444 census tracts, with a mean score of 100, where higher is more compact.
  1. **Density**: residential and employment.
  2. **Land-use mix**: homes, jobs and services together or apart.
  3. **Centering**: the strength of downtowns and subcentres.
  4. **Street connectivity**: intersection density, the share of 4-way junctions, block size.
- **For us**:
  - These four are the *knobs* that distinguish a compact pre-war town from a sprawling postwar one.
  - They are also the *test*: compute the index on a generated district and check it lands where its era says it
    should.

Sources: [Who sprawls the most? (Johns Hopkins)](https://publichealth.jhu.edu/center-for-smart-transportation/research/who-sprawls-the-most);
[Technical report](https://americanhealth.jhu.edu/sites/default/files/2026-05/Who%20Sprawls%20the%20Most_TECHNICAL%20FINAL.pdf);
[NCI sprawl report](https://gis.cancer.gov/tools/urban-sprawl/sprawl-report-short.pdf);
[EHP sprawl factors table](https://pmc.ncbi.nlm.nih.gov/articles/PMC2957923/table/t1-ehp-118-1425);
[Sprawl score code](https://github.com/walkabillylab/sprawl_score).

## How the street pattern changed (Southworth and Ben-Joseph; Boeing)

| Era | Pattern | Block | Junctions |
|---|---|---|---|
| to ~1900 | Fine gridiron, 66 ft (1-chain) streets, alleys | 300-400 ft | 4-way, dense |
| 1890-1930 | Streetcar suburb: rectangular grid, long thin blocks, alleys | 600 x 250 ft | 4-way |
| 1930-1950 | "Fragmented parallel" and warped grid; FHA guidance | 800+ ft | some T-junctions |
| 1950-1990 | Loops and lollipops: curvilinear loops, culs-de-sac, collector spine | 1,000+ ft or none | 3-way, dead ends |
| 2000- | New Urbanist and connectivity rules: rebounding grids | 400-600 ft | more 4-way |

- **The driving institutions**: the FHA (underwriting new subdivisions only if they followed its design standards)
  and the ITE (whose 1965 *Recommended Practices for Subdivision Streets* advised internal disconnection, avoiding
  4-way junctions, and loops and culs-de-sac).
- **Boeing, "Off the Grid... and Back Again?" (JAPA 2020)**:
  - Griddedness, orientation order, straightness, 4-way share and intersection density *fell* from 1940 to the
    1990s, while dead ends and block length rose.
  - Since 2000 the trends have partly reversed.
- **Boeing, urban spatial order (100 cities)**: US and Canadian cities are far more gridded (lower bearing entropy and
  circuity) than elsewhere. Chicago is the most gridded and Charlotte the least.
- **For us**: these are *measured targets*. Each era's district must hit its era's numbers:
  - bearing entropy;
  - average node degree (about 3.0-3.2 in a grid, about 2.6-2.8 in a cul-de-sac subdivision);
  - dead-end share;
  - intersection density (about 100-250 per km² in grids, 30-60 in subdivisions).
  - **OSMnx** computes all of these on real towns, so we can calibrate against real Great Lakes towns by name
    (research/demographics/community_profiles).

Sources: [Off the Grid... and Back Again? (arXiv)](https://arxiv.org/pdf/2010.04771);
[Boeing publication page](https://geoffboeing.com/publications/off-the-grid-japa/);
[Southworth and Ben-Joseph, reconsidering the cul-de-sac (MIT)](https://web.mit.edu/ebj/www/doc/culdesacs.pdf);
[Access magazine version](https://www.accessmagazine.org/spring-2004/reconsidering-cul-de-sac/embed/);
[Urban spatial order: orientation and entropy (Boeing)](https://geoffboeing.com/publications/urban-spatial-order-entropy/);
[Modeling urban networks with OSMnx](https://arxiv.org/pdf/2505.00736);
[Street configuration and accessibility (Neptis)](https://neptis.org/publications/chapters/street-configuration-and-neighbourhood-accessibility).

## The postwar suburb (Levittown and the FHA)

- **Levittown, NY (1947)**: 17,447 near-identical houses on 60 x 100 ft lots for veterans, every mortgage
  FHA-insured. It was the model for mass-produced subdivisions.
- **What the FHA's standards required**: curving streets, large lots, a single use and setbacks. Underwriting
  favoured new suburban houses over older urban ones, which drained the old districts (the rent gap, 03).
- **What it looks like**:
  - Repeated house models (3-5 per tract, mirrored and recoloured).
  - Wide front lawns, a driveway per house, no alleys.
  - A school at the centre and a shopping centre at the arterial corner.

Sources: [HOLC + FHA maps (The Metropole)](https://themetropole.blog/2023/08/16/pair-holc-maps-with-fha-maps-to-tell-a-more-complete-story/);
[Postwar suburbs (USC Scalar)](https://scalar.usc.edu/works/housing-inequality/inequality-in-housing-post-wwii-urban-flight-and-the-creation-of-the-suburbs.29);
[Postwar co-ops and redlining (NPQ)](https://nonprofitquarterly.org/postwar-interracial-co-ops-and-the-struggle-against-redlining/).

## The commercial strip and the edge city

- **The strip (or "stroad")**: commercial uses zoned along the arterial in a band one lot deep. Each lot is a
  free-standing building behind its own car park, with a curb cut per lot, so there are many conflict points, and
  traffic ends up both fast and slow.
  - The pattern comes from use zoning plus parking minimums plus arterial frontage.
- **The edge city (Garreau, 1991)**: 5M+ sq ft of offices, 600k+ sq ft of retail, more jobs than bedrooms, perceived as
  one place, and not a city 30 years before.
  - Built at freeway interchanges, with mid-rise offices in parking fields and winding parkways without sidewalks.
  - Too big for our towns, but a *small-scale echo* (the interchange cluster: motel, gas, fast food, a plant) fits a
    6-10k town at its highway exit.

Sources: [Edge city (Wikipedia)](https://en.wikipedia.org/wiki/Edge_city);
[Revisiting the edge city (Planetizen)](https://planetizen.com/node/98223);
[Strong Towns: setbacks](https://strongtowns.org/journal/2019/2/22/question-of-the-week-why-are-building-setbacks-sometimes-undesirable?format=amp).

## Urban growth models (simulating sprawl)

- **SLEUTH** (Clarke, mid-1990s): a cellular automaton. Its name comes from its inputs: Slope, Land use, Excluded
  land, Urban extent, Transportation and Hillshade.
  - **Four growth rules**: spontaneous growth, new spreading centres, edge growth, and road-influenced growth.
  - **Five coefficients**: dispersion, breed, spread, slope resistance, and road gravity.
  - It has been calibrated on 100+ cities.
  - **For us**: the five coefficients are an economical description of *how a town grows*.
    - High spread with low dispersion gives compact edge growth.
    - High road gravity gives ribbon development along highways (the strip).
    - Breed gives leapfrog subdivisions.
- **The catch**: SLEUTH is iterative (each step depends on the last), which breaks our locality rule. Use it
  offline, to grow a town's *extent* once per seed, and keep per-chunk detail local (06).

Sources: [SLEUTH on Tehran (arXiv)](https://arxiv.org/pdf/1708.01089);
[Silva and Clarke 2005 (UCSB)](https://people.geog.ucsb.edu/~kclarke/Silva&Clarke2005.pdf);
[SAMBI urban growth modelling (USGS)](https://sciencebase.gov/catalog/item/5506f6dbe4b02e76d756e4d8).
