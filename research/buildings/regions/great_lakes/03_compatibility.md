# What looks good next to what: compatibility (2026-10-05)

The question: given a building, which neighbours look right beside it? Two bodies of work answer it:

- **Historic district design review** gives explicit, tested criteria, used by hundreds of commissions for decades.
- **Environmental psychology** gives measured preference.

## 1. The visual compatibility criteria (design review)

- **Origin**: the *Secretary of the Interior's Standards* (new construction must be "compatible" and also
  "differentiated"). Local ordinances turn this into a list of **visual compatibility factors**.
- **The list**: the same 10-16 factors recur almost word for word from Sioux Falls to St. Paul to Nashville.

| Factor | The rule |
|---|---|
| **Height** | Within the range of the buildings it is "visually related" to, usually ±1 storey of its neighbours |
| **Proportion of the front facade** | The ratio of width to height matches its neighbours (a narrow vertical shopfront among narrow vertical shopfronts) |
| **Proportion of openings** | Window and door shapes (vertical double-hungs versus horizontal ribbons) match |
| **Rhythm of solids to voids** | The pattern of wall and window across the facade matches |
| **Rhythm of spacing** | The gaps between buildings, and their widths, keep the street's beat (25 ft shopfronts; 40-50 ft houses with 10-15 ft gaps) |
| **Rhythm of entrances and porches** | Doors and porches at the same intervals and level |
| **Relationship of materials, texture and colour** | Not contrasting greatly with the dominant palette (red brick beside red brick; painted wood beside painted wood) |
| **Roof shape** | The dominant roof form and pitch continued (gables among gables; flat with cornices on Main Street) |
| **Walls of continuity** | Street walls continued (a commercial block keeps zero setback) |
| **Scale** | The size of parts relative to people (door height, window size, storey height) |
| **Directional expression** | Vertical, horizontal or non-directional, as the neighbours are |
| **Setback** | Front and side setbacks within the range of the block |

- **The principle** is **"compatible but differentiated"**: a new building repeats its neighbours' *proportions,
  rhythm, height, setback and roof* and is free in its *details*. It is the *same grammar with a different
  vocabulary*.
  - **For us** this sets the hierarchy of what must match between neighbours:
    1. setback and street wall;
    2. height and scale;
    3. proportion and rhythm;
    4. roof;
    5. materials and colour;
    6. ornament (free to differ).

Sources: [Sioux Falls standards for new construction](https://www.siouxfalls.gov/files/assets/public/v/1/city-government/boards-amp-commissions/board-of-historic-preservation/standards-for-new-construction-rehab.pdf);
[South Dakota visual compatibility rule](https://sdlegislature.gov/api/Rules/15909.docx);
[Ridgewood NJ code](https://www.zoneomics.com/code/ridgewood-NJ/chapter_38);
[Chattanooga historic district review narrative](https://www.thempc.org/eagenda/x/hrb/2022/june-8-2022-historic-district-board-of-review/submittal-packet-narrative_39.pdf);
[St. Paul HPC: 617 Laurel](https://www.stpaul.gov/sites/default/files/Media%20Root/Planning%20%26%20Economic%20Development/617%20Laurel%20packet%20for%20web.pdf);
[St. Paul HPC: 1498 Summit](https://www.stpaul.gov/sites/default/files/Media%20Root/Planning%20%26%20Economic%20Development/1498%20Summit%20packet.pdf).

## 2. What the preference research adds

- **Is compatibility only taste?** Groat ("Contextual Compatibility in Architecture", 1988, University of Michigan)
  tested it. Lay viewers and architects alike prefer infill that **replicates the facade's composition and massing**
  (the "replication" and "abstract reference" strategies) over infill that contrasts.
  - Matching the site's **massing and setback mattered more than matching ornament**, which confirms the hierarchy
    above.
- **Order with complexity** (Stamps; Nasar; 02_styles §5): a street of varied buildings pleases when the variation
  is organised (shared cornice line, shared bay rhythm). It displeases when every building breaks the pattern.
- **Upkeep beats style**: Nasar's respondents rated well-kept plain buildings above dilapidated handsome ones.
  - **For us**: a district's condition is a first-order visual variable, not dressing.
- **Naturalness**: trees, lawns and planting raise preference everywhere. Street trees soften mismatches.

Sources: [Linda N. Groat (Wikipedia)](https://en.wikipedia.org/wiki/Linda_N._Groat);
[Nasar, The Evaluative Image of the City](https://uk.sagepub.com/en-gb/mst/the-evaluative-image-of-the-city/book4980);
[Facade complexity preference (U. Sydney)](https://ses.library.usyd.edu.au/handle/2123/18981);
[Streetscape visual entropy](https://www.avantipublishers.com/index.php/ijaet/article/view/1450).

## 3. Rules for the generator: neighbour constraints

These go in the engine as constraints between adjacent lots.

1. **Hard: share these with the block.** Generate the block's *frame* first, then the buildings:
   - **setback band**: the block median ±10 % on residential blocks, 0 on commercial frontage;
   - **cornice or eave line**: commercial neighbours within 1 storey; a dominant cornice height per block face;
   - **lot rhythm**: the subdivision's lot width (urban_layout §parcels);
   - **roof family**: gable, hip or flat by era band.
2. **Soft: draw from the band's distribution**:
   - style (with the era lag, 02 §2);
   - wall material from the band's palette (brick-dominant inside the old fire limits, wood siding outside);
   - colour from a palette that keeps neighbours from repeating exactly.
3. **Free**: ornament, porch details, colour within the palette, sign content.
4. **Repetition is allowed**: catalogue and builder models repeat. A postwar tract has 3-5 models, mirrored, with
   recoloured trim. Pre-war blocks rarely repeat the same house twice in a row.
5. **Breaks are deliberate.** Civic landmarks (the church, courthouse, school) *should* break height, setback and
   style. That is how they become landmarks (Lynch).
6. **Upkeep follows the district**: condition comes from the district state (urban_layout 03), with small per-lot
   noise. Neighbours' conditions correlate.
