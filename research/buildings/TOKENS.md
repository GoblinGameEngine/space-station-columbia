# Building tokens: how a photo becomes data (2026-10-05)

The user: "collect images of real estate and tokenize the images. I want you to have a perfect understanding of what
is where and why, so that we can make a procedural generation engine for buildings."

A token file describes **one building as seen in one or more images** in a closed vocabulary
(`tools/buildings/vocab.json`), so a corpus can be counted, cross-tabulated and turned into generator probabilities.
It records three things:

- **what**: the parts, as `family:value` tokens;
- **where**: their positions, in a facade grid and on the lot;
- **why**: each notable token's cause, linked to the research files.

The structure follows the procedural-building literature and the vehicle fleet:

1. **Context**: the lot and street.
2. **Mass**: the blocks and roofs.
3. **Facade**: floors, bays and openings.
4. **Dressing**: style, materials, details.
5. **State**: condition and changes.

(Müller et al. 2006; McAlester's form-before-style; Longstreth's composition types:
regions/great_lakes/02_styles.md.)

## File: `research/buildings/regions/<region>/tokens/<ID>.json`

```json
{
  "id": "GL-0001",
  "images": [{"file": "remake/reference/HF-012/photo_1.jpg", "view": "front_34", "source": "HABS IL-1234",
              "url": "https://www.loc.gov/item/il0999/", "license": "public domain", "author": "...", "photo_year": 1934}],
  "place": {"town": "Galesburg", "state": "IL", "transect": "T3", "band": "railroad_1870_1900"},
  "year_built": 1892,
  "tokens": ["use:house", "form:upright_and_wing", "style:greek_revival_folk", "storeys:1.5", "..."],
  "mass": [
    {"block": "main", "w_ft": 20, "d_ft": 28, "storeys": 1.5, "roof": "gable", "ridge": "perpendicular_to_street", "pitch": "9:12"},
    {"block": "wing", "side": "right", "w_ft": 18, "d_ft": 16, "storeys": 1, "roof": "gable", "ridge": "parallel_to_street", "pitch": "8:12"}
  ],
  "facade": {
    "faces": "street",
    "floors": ["W . W", "W D W"],
    "notes": "gable-end attic window over two upper windows; door off-centre in the wing"
  },
  "lot": {"setback": "deep", "side_gap": "wide", "driveway": "right", "garage": "detached_rear", "fence": "none", "trees": "yard_mature"},
  "why": [
    {"token": "form:upright_and_wing", "cause": "folk", "ref": "great_lakes/02_styles.md §1", "note": "Yankee migration stream, NY to MI/OH"},
    {"token": "foundation_exposure:high", "cause": "climate", "ref": "great_lakes/01_codes.md §2 R403", "note": "frost depth, basement"}
  ],
  "catalog": {"kind": "house", "archetype": "upright_and_wing"},
  "confidence": "high",
  "annotator": "claude 2026-10-05"
}
```

## The facade grid (the "where")

- Each street face is one string per floor, **top floor first**, one character per bay, read left to right as seen
  from the street:
  - `W` window; `Wp` a pair; `Wb` a bay window; `Wd` a dormer (in the roof floor); `D` a door; `G` a garage door;
  - `S` a storefront (display glass); `E` an entrance recessed in a storefront; `T` a transom band;
  - `.` blank wall; `C` a chimney breast; `|` a pilaster or party wall; `P` a porch post bay.
- **Roof floor**: the topmost string when there's a gable window, dormers or a parapet sign (`N` a sign band).
- **Example**, a two-part commercial block, 3 bays:
  - `["N N N", "W W W", "S E S"]`: a sign band in the parapet, three upper windows, and a storefront with a recessed
    door.
- **Why a grid**: it is the split-and-repeat structure of CGA (floors, then bays). Grids can be compared across the
  corpus ("how often is the door in the middle bay?") and fed straight to a facade generator.

## Token families (see vocab.json for the closed values)

| Stage | Families |
|---|---|
| Context | `use`, `transect`, `band` (era band), `setting` (street type: main_street, residential_grid, cul_de_sac, arterial_strip, rural_road, farmstead, waterfront), `lot_w` (narrow/standard/wide), `setback`, `side_gap`, `corner` (yes/no) |
| Mass | `form` (McAlester / folk / Longstreth types), `storeys`, `footprint` (rect, L, T, U, irregular), `wing`, `roof`, `pitch` (low/mid/steep), `roof_mat`, `ridge` (parallel/perpendicular to the street), `dormer`, `chimney`, `foundation`, `foundation_exposure`, `garage`, `porch` |
| Facade | `bays`, `symmetry` (symmetric/asymmetric), `door_pos` (centre/side/corner), `window`, `window_group` (single/pair/ribbon/bay), `window_proportion` (vertical/square/horizontal), `sill` (low/standard/high), `storefront` (traditional/recessed_entry/modern_glass/infilled/none), `transom`, `sign` |
| Dressing | `style`, `wall`, `wall_accent`, `trim`, `cornice`, `ornament` (bracket, dentil, spindle, half_timber, shutters, quoins, lintel_stone, ...), `colour_body`, `colour_trim` (named families), `porch_post`, `rail` |
| State | `condition` (kept/worn/shabby/boarded), `alteration` (vinyl_over_wood, replacement_windows, infilled_storefront, enclosed_porch, added_ramp, added_dormer, ...), `vacancy` |

## The causes (the "why")

Each `why` entry names one cause from a closed list, and a reference into the region's research:

| cause | Meaning | Example |
|---|---|---|
| `code` | A building-code rule | the egress window sill; blank walls at the lot line; parapets at fire walls |
| `zoning` | A land-use rule | the front setback; parking in front (the strip); the single use |
| `climate` | Weather and site | the frost line, so a basement and a high foundation; snow, so a steep roof; the deep porch |
| `folk` | A carried tradition | the I-house; upright-and-wing; the Ontario cottage |
| `fashion` | The style of the day, via pattern books, catalogues, builders | the Queen Anne spindles; ranch picture windows |
| `economics` | Cost, land price, mass production | the narrow lot, so a gable-front; the catalogue house; the decorated shed |
| `technology` | What could be built | balloon frame; plate glass storefronts; aluminium and vinyl; mass timber |
| `use` | What happens inside | upper-floor flats over shops; drive-throughs; loading docks |
| `context` | Fitting the neighbours | the matching cornice line; the setback held |
| `change` | Later alteration | vinyl siding; an enclosed porch; an infilled storefront |

## Rules for annotators

1. **Annotate only what can be seen.** If a part is hidden, leave it out. Don't guess dimensions to the foot: use the
   relative families (narrow/wide, low/steep) unless a measured drawing gives numbers. HABS drawings → `w_ft`/`d_ft`
   exact, and `"confidence": "measured"`.
2. **Form before style.** Decide `form` from the mass (roof plus footprint plus storeys) before choosing a `style`.
   Most buildings in the region are folk or vernacular with a little style applied: say so (`style:vernacular`
   plus `ornament:` tokens) rather than forcing a named style.
3. **Every alteration is a token.** Vinyl over clapboard, replacement windows and infilled storefronts are what make a
   generated town look lived-in (the district state of urban_layout/03).
4. **The why list is for the non-obvious.** Give a cause for every `form`, and for any token that a generator could
   get wrong without the rule (sills, blank walls, foundation height, parapets, parking).
5. **Values outside the vocabulary**: use the nearest value and add the observation to `facade.notes`. If a value
   keeps recurring, add it to vocab.json and record that in the region's CHANGELOG.

## Tools

- `tools/buildings/check_tokens.py <region>`: validates every token file against vocab.json and reports unknown
  values.
- `tools/buildings/token_stats.py <region>`: counts tokens and cross-tabulates them (form x band, roof x form,
  door_pos x form, ...). Its tables are what the generator's probabilities come from.
