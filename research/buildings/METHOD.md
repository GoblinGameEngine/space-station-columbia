# Building and lot research: the method (repeat it for every region)

The user, 2026-10-05: "I want you to document what you reference and why, as we will be repeating this research again
for different geographical areas around the expanded map."

This is the procedure that produced `regions/great_lakes/`. A new region (another culture area of the 100 km x 20 km
station) gets its own `regions/<region>/` folder built the same way, so the generator can read every region in the
same shape.

## 0. Define the region

- **Name it** after the founders' source area (the bible says who settled where), list its states and provinces, and
  note its climate (IECC climate zones, frost depth, snow load).
- **Write `regions/<region>/README.md`** with that definition and a CHANGELOG.

## 1. Codes: `01_codes.md`

- **Sources, in order of preference**:
  1. The adopting body's own pages (state building boards, legislative code sites: free official text).
  2. ICC summaries and the model code (IRC/IBC/IECC) sections for numbers.
  3. Government histories (NPS Preservation Briefs) for code history.
  4. A municipal ordinance or two as examples of local rules (fences, setbacks).
- **Collect only provisions that change what a building or lot looks like**: windows and egress, stairs and
  foundations (frost), roofs (snow and slope), separation and openings near lot lines, construction types and
  heights, parapets and fire walls, accessibility, energy (wall thickness, glazing).
- **Also collect the region's code history**: which code family ruled when (BOCA in the Great Lakes), local fires and
  disasters that changed the rules, fire limits.
- **Mark numbers taken from memory with †**, to be verified against the code text.

## 2. Style scholarship: `02_styles.md`, `03_compatibility.md`, `04_futures.md`

- **The canon to check for every region**:
  - **Identification**: a field guide (McAlester for the US) for the form-before-style rule.
  - **Folk geography** (Kniffen, Glassie, regional folk-housing studies): the region's carried house types and
    migration streams.
  - **Fashion diffusion**: pattern books, catalogue houses, builders' plans for the region's eras.
  - **Commercial composition** (Longstreth) and the roadside (Venturi).
  - **Generative grammars** (Stiny and Mitchell; Koning and Eizenberg; Müller et al.): how to encode a style.
  - **Preference** (Appleton, Hildebrand, Nasar, Stamps, Groat).
  - **Compatibility**: design-review criteria from several cities.
  - **Futures**: energy codes, prefab, mass timber, retail change.
- **Region-specific additions**: the local heritage bodies' style guides (here: Ontario Heritage Trust, Texas Historical
  Commission's style sheets as a general key, municipal historic-district guides).
- **Write each claim with its source inline**, plus a "For us" line saying what the generator does with it.

## 3. Photos: `corpus.json` → `tools/buildings/fetch_corpus.py`

- **First, survey what we already have**: remake/reference/ (the catalog's photos and HABS drawings). Count it by
  catalog kind and decade (the snippet in this method's history: ~4,100 photos, 848 drawings, mostly pre-1950).
  Collect only the **gaps**.
- **Sources, chosen for clear reuse terms** (the licence travels with each file in `sources.json`):
  - **Library of Congress HABS/HAER** (public domain): photographs and **measured drawings**, the best source for
    exact dimensions (`remake/tools/refs.py loc-*`).
  - **Wikimedia Commons curated categories** ("Ranch-style houses in Ohio", "Strip malls in Michigan"): public
    domain, CC0, CC BY or CC BY-SA only.
  - **Public assessor photos** where a county has released them. Lucas County, Ohio's ~97,000 block cards via DPLA
    are the closest open equivalent to real-estate listing photos. Search buckets sample them at seeded offsets.
  - **Not used**: listing sites (Zillow, Realtor, MLS) and builder renders. Their photos are copyrighted and their
    terms forbid scraping. The parked modern-buildings library on the Windows PC holds some for private reference
    only (memory: ssc-modern-buildings-research).
- **Each bucket names its categories or search and a count**. The fetch is deterministic (seed), so a rerun gets the
  same files.
- **Size**: 1,280 px wide (enough for annotation). The corpus is ~11 MB for ~45 files.

## 4. Tokens: `regions/<region>/tokens/<ID>.json` (TOKENS.md)

- **Make 2x2 contact sheets** (`tools/buildings/sheet.py`) and annotate each building in the closed vocabulary
  (`tools/buildings/vocab.json`) with `tools/buildings/tok.py` (which copies licence and source from `sources.json`).
- **Order**:
  1. context;
  2. mass (form before style);
  3. facade grid;
  4. dressing;
  5. state;
  6. lot and boundaries;
  7. **why**: a cause and a reference for every form and every non-obvious token.
- **Exclude off-target images** (a category's stray interior, an out-of-region example) and log why in the CHANGELOG.
  Out-of-region examples of a *type* can stay if the type is the point (a Lustron is a Lustron), with the place
  recorded truthfully.
- **Validate** with `tools/buildings/check_tokens.py <region>`. Extend the vocabulary only deliberately, logged in the
  CHANGELOG.
- **Count** with `tools/buildings/token_stats.py <region> [famA famB]`: those tables become the generator's
  probabilities.

## 5. Lots: `lot_samples.json` → `tools/buildings/lot_sample.py` (LOTS.md)

- **Parcels**: a state or county open parcel layer. Wisconsin's statewide V11 layer (via the WI DNR map service) was
  used here. **Never fetch owner names or addresses**: the sampler's outFields exclude them.
- **Buildings and streets**: OSM via Overpass (ODbL). **Aerials**: NAIP via the USGS National Map (public domain).
- **Sample one area per circumstance**:
  - prewar alley grid, streetcar belt, small-town main street and residential, village;
  - planned interwar, postwar tract, 1970s cul-de-sac, wooded curvilinear, 1990s and current subdivisions,
    New Urbanist;
  - garden apartments, condos, mobile home park;
  - arterial strip, mall or big box, industrial;
  - lakeshore or resort, farmland.
- **Locate areas** by OSM features (turning circles for culs-de-sac, residential=trailer_park, building=apartments)
  or Nominatim. **Always check the NAIP contact sheet** before measuring (two first guesses here landed on the wrong
  kind of place).
- **Read the renders** for boundaries (hedges, tree lines, mow lines, fences where visible) and write the
  per-setting table.

## 6. Centres and industry: `urban_layout/centers_samples.json` → `tools/buildings/center_sample.py`

- **Measure** anchors, juniors, in-line shops and pads, parking ratio and tenant tags at a few real centres and parks
  per region.
- **Check the generator ranges** (`tools/settlegen/centers.py`) against them.

## 7. Bibliography: `regions/<region>/BIBLIOGRAPHY.md`

- Every source with **what it is, what we took from it, and why we chose it over alternatives**.
- **Reuse rule**: cite, link and summarise; never copy copyrighted text or images into the repo.

## Region checklist

- [ ] README + CHANGELOG
- [ ] 01_codes, 02_styles, 03_compatibility, 04_futures
- [ ] corpus.json fetched; gaps filled; tokens annotated and validated
- [ ] lot_samples.json measured; boundary table written
- [ ] centres and industry measured
- [ ] BIBLIOGRAPHY.md
- [ ] token_stats tables saved for the generator
