# Urban planning and urban form: why towns take the shapes they do (2026-10-05)

## Classic land-use models (the shape of the whole town)

| Model | Year | Shape | What drives it |
|---|---|---|---|
| **Burgess concentric zones** | 1925 | Rings round the centre: CBD, zone of transition, working-class homes, middle-class homes, commuter zone | Growth pushes each ring outward ("invasion and succession"); income rises with distance |
| **Hoyt sectors** | 1939 | Wedges along transport lines | A sector keeps its character as it extends: working-class wedges follow rail and industry; high-income wedges follow amenity (water, high ground, a university) |
| **Harris and Ullman multiple nuclei** | 1945 | Several centres (CBD, industrial district, university, outlying business district) | Some activities cluster and others repel; separate centres grow |
| **Alonso bid-rent** | 1964 | Rings, by who outbids whom | Each use bids for land by its need for centrality: commerce > industry > dense housing > sparse housing > farming |

- **For us**: none of these models is right alone, and each supplies a rule.
  - **Burgess**: the *age gradient* (the oldest fabric at the centre).
  - **Hoyt**: *sector persistence* (class follows a rail line or a shore outward).
  - **Multiple nuclei**: *secondary centres* (the plant, the college, the highway interchange).
  - **Bid-rent**: the *price field* that decides which use takes a free lot.

Sources: [Concentric, sector, multiple nuclei compared (Cognito)](https://cognito.org/blog/ap-human-geography-models);
[Internal structure of cities (Cognito)](https://cognito.org/courses/ap/humangeog/notes/SkxEUmpWVHU/6.5-the-internal-structure-of-cities);
[Urban landscape (Save My Exams)](https://www.savemyexams.com/as/geography/aqa/16/revision-notes/contemporary-urban-environments/urban-forms/urban-landscape/).

### Density falls off exponentially (Clark 1951; Bertaud)

- **Clark's law**: population density declines as a negative exponential of distance from the centre,
  ρ(r) = ρ₀·e^(−b·r). This has been confirmed across hundreds of cities.
- **Bertaud (*Order Without Design*, 2018)**:
  - the gradient *flattens* as cities get richer and transport gets faster;
  - cities are best read as labour markets shaped by their transport networks, not as designed objects.
- **For us**: one ρ₀ and one b per settlement, with b set by the founding era (walking town: steep; car town: flat).
  This gives every lot a target density without reference to its neighbours, which keeps the rule local.

Sources: [Testing the monocentric model (arXiv)](https://arxiv.org/pdf/2111.02112);
[Alain Bertaud (Wikipedia)](https://en.wikipedia.org/wiki/Alain_Bertaud);
[Order Without Design reviewed (NYU Stern)](https://www.stern.nyu.edu/experience-stern/news/senior-research-scholar-alain-bertaud-s-book-order-without-design-reviewed.md).

## The hierarchy of settlements (Christaller, 1933)

- **Threshold**: the smallest population that will support a good or service. A general store needs a few hundred
  people; a hospital, tens to hundreds of thousands.
- **Range**: how far people will travel for it.
- **The resulting pattern**:
  - Low-order goods (bread, a bar, a gas station) appear everywhere.
  - High-order goods (a department store, a courthouse, a hospital) appear only in larger places.
  - Market areas tile as hexagons, giving many villages, fewer towns and one city.
- **For us**: this sets *what each settlement has*, by population tier.
  - Our population-tier research (research/population_tiers/) already carries storefront counts.
  - Christaller adds the *spacing* rule between settlements and the rule that a village's high-order needs are met
    in the next town, which creates traffic between them (04).

Sources: [Central place theory (Wikipedia)](https://en.wikipedia.org/wiki/Central_place_theory);
[Christaller and Lösch (INFLIBNET)](https://ebooks.inflibnet.ac.in/geop09/?p=123);
[NVCC: central place theory](https://pressbooks.nvcc.edu/nolgeo210/chapter/12-4-central-place-theory/).

### Retail catchments (the commercial building blocks, with real sizes)

| Centre | Typical GLA | Anchor | Trade area |
|---|---|---|---|
| Convenience / strip | up to 30,000 sq ft (3+ stores) | convenience store, dry cleaner | walk or 1 mile |
| Neighbourhood | ~60,000 sq ft (30-150k) | supermarket | ~3 miles |
| Community | ~150,000 sq ft (100-500k) | discount department store | 3-6 miles, 20-minute drive |
| Regional / super-regional mall | 400k-1M+ sq ft | 2+ department stores | 5-25 miles |

Sources: [ICSC shopping centre definitions](https://www.icsc.com/uploads/research/general/Canadian-Shopping-Centre-Definitions.pdf);
[Retail trade analysis: Reilly, Huff](https://open-exam-prep.com/study-guides/ccim/ch8-commercial-sectors/retail-market-analysis);
[HUD: neighbourhood retail development](https://archives.huduser.gov/oup/conferences/presentations/hbcu/sanantonio/neighborhood_retail_dev.pdf).

## The neighbourhood unit (Perry, 1929)

- **Size**: a neighbourhood sized to one elementary school, 5,000-9,000 residents on about 160 acres at about
  10 dwellings an acre.
- **The school**: at the centre, a quarter-mile walk (at most half a mile) for every child, with no arterial to
  cross.
- **Edges**: arterials bound the unit and pass round it, not through it.
- **Centre and corners**: shops sit at the corners where arterials meet, and parks and civic buildings at the
  centre.
- **Legacy**: most planned suburbs since 1930 are built from this cell. With cul-de-sacs added it becomes the postwar
  subdivision (05).
- **Alexander's Pattern Language agrees on the scale**: "Community of 7000" (5,000-10,000 people) and
  "Identifiable Neighbourhood" (about 500 people, about 300 yards across).

Sources: [Neighbourhood unit (Wikipedia)](https://en.wikipedia.org/wiki/Neighbourhood_unit);
[APA PAS report 141: neighbourhood boundaries](https://planning.org/pas/reports/report141.htm);
[A Pattern Language (Wikipedia)](https://en.wikipedia.org/wiki/A_Pattern_Language);
[Pattern list (carfree.com)](https://carfree.com/patterns.html).

## How people read a town (Lynch, 1960) and what makes it live (Jacobs, 1961)

- **Lynch, *The Image of the City***: people build a mental map from five elements.
  - **Paths**: streets, rail, canals.
  - **Edges**: shores, rail lines, walls, steep ground.
  - **Districts**: areas of recognisable character.
  - **Nodes**: squares, junctions, stations.
  - **Landmarks**: a water tower, a steeple, the elevator.
  - **For us**: these are the *legibility checklist* for a generated town. Each needs at least one strong landmark
    per district and nameable edges.
- **Jacobs, *The Death and Life of Great American Cities***: diversity needs all four of these generators.
  - **Mixed primary uses**: people about at different hours.
  - **Short blocks**: route choice, and more corners to put businesses on.
  - **Aged buildings of mixed age**: cheap rents for marginal businesses.
  - **Density.**
  - **For us**: these explain why the old downtown has the odd little businesses and the new strip does not. They
    are also the rules the story engine can test a district against.

Sources: [The Image of the City (Wikipedia)](https://en.wikipedia.org/wiki/The_Image_of_the_City);
[Lynch's elements (Wikibooks)](https://en.wikibooks.org/wiki/Reading_the_City_Through_History_and_Law/Image_of_the_City);
[Jacobs review (San Antonio Report)](https://sanantonioreport.org/book-review-the-death-and-life-of-great-american-cities-by-jane-jacobs/);
[Quantifying urban diversity (GMU)](https://mars.gmu.edu/handle/1920/6355).

## Movement shapes use (space syntax; Hillier)

- **Natural movement**: the street network's configuration alone predicts much of the pedestrian flow, before any
  land use is placed.
- **Integration**: a measure of how few turns it takes to reach everywhere else from a street. Highly integrated
  streets carry more people, more ground-floor shops and less crime.
- **For us**:
  1. Lay out the streets.
  2. Compute each segment's integration (or, more cheaply, its betweenness on the generated graph).
  3. Let commerce take the most integrated frontage.
  - This is how a real Main Street "chooses" itself, and it gives emergent placement instead of hand-placed
    downtowns.

Sources: [Space syntax (Wikipedia)](https://en.wikipedia.org/wiki/Space_syntax);
[Hillier's legacy: a synopsis](https://0-doi-org.brum.beds.ac.uk/10.3390/su13063394);
[Cities as movement economies](https://theccd.org/spotlight-research/cities-as-movement-economies/).

## Scaling laws (Bettencourt, West)

- **Superlinear** (β ≈ 1.15): GDP, wages, patents and disease cases per person grow with city size.
- **Sublinear** (β ≈ 0.85): infrastructure (road length, cables, pipes) grows more slowly than population.
- **For us**: a sanity check on totals.
  - Road length ∝ P^0.85 across our settlements.
  - Per-capita shops and services rise slightly with size.

Sources: [Urban scaling (Wikipedia)](https://en.wikipedia.org/wiki/Urban_scaling);
[Urban scaling laws (arXiv 2404.02642)](https://arxiv.org/pdf/2404.02642);
[APA Planning, Dec 2015](https://planning.org/planning/2015/dec/research.htm).

## Eras of growth (Warner, *Streetcar Suburbs*, 1962)

- **Walking city**: about a 2-mile radius (Boston 1850). Mixed and dense.
- **Horsecar**: commutes out to about 4 miles.
- **Electric streetcar** (1888 on): about 6 miles. Lines of narrow-lot middle-class suburbs, with shops at the
  stops.
- **Automobile** (1920s on, mass after 1945): low density, filling the spaces between the streetcar fingers.
- **For us**:
  - Each era leaves a recognisable band and its own street pattern (05).
  - Each settlement's founding era and growth eras decide which bands it has.
  - SSC's road trams fit the streetcar band: the bible gives the station trams, so its towns can grow streetcar
    fingers.

Sources: [Streetcar Suburbs (Harvard UP record)](https://oeaw.ac.at/resources/Record/9780674044890);
[Streetcar suburbs (Sage urban history)](https://sk.sagepub.com/ency/edvol/embed/urbanhistory/chpt/streetcar-suburbs);
[The walking city](https://bnjd.substack.com/p/differing-historical-perspectives).
