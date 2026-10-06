# Building research: for the procedural building and lot generator

The user, 2026-10-05: research building codes for the target area; collect and tokenize real-estate images; scholarly
work on why buildings are styled as they are, what looks good together, and future buildings; tokenize lots ("a fine
fundamental understanding of how lots are sized and arranged for all circumstances"); "document what you reference
and why, as we will be repeating this research again for different geographical areas around the expanded map."

| File | What |
|---|---|
| [METHOD.md](METHOD.md) | The repeatable procedure, per region |
| [TOKENS.md](TOKENS.md) | How a photo becomes data: the token file, the facade grid, the causes |
| [LOTS.md](LOTS.md) | Lots: why their sizes, measured Wisconsin lots in 21 circumstances, boundaries, lot tokens, generator rules |
| [modern_buildings_and_subdivisions.md](modern_buildings_and_subdivisions.md) | The parked 2026-09-29 notes (from branch laptop-building-research) |
| regions/great_lakes/ | The first region: [01_codes](regions/great_lakes/01_codes.md), [02_styles](regions/great_lakes/02_styles.md), [03_compatibility](regions/great_lakes/03_compatibility.md), [04_futures](regions/great_lakes/04_futures.md), [BIBLIOGRAPHY](regions/great_lakes/BIBLIOGRAPHY.md), [CHANGELOG](regions/great_lakes/CHANGELOG.md), corpus.json, lot_samples.json, tokens/, lots/ |

**Related**: ../urban_layout/ (towns: zoning, form, change, traffic, sprawl, procgen;
[07_centers_and_industry.md](../urban_layout/07_centers_and_industry.md)); ../lot_contents/ (what is on a lot);
../building_catalog/; remake/research/CATALOG_SPEC.md (the existing builders' trait vocabulary).

**Tools**:
- tools/buildings/: fetch_corpus.py, sheet.py, tok.py, vocab.json, check_tokens.py, token_stats.py, lot_sample.py,
  center_sample.py
- tools/settlegen/centers.py (generators) and preview_centers.py

**Images**:
- Photos: remake/reference/corpus_<region>_<bucket>/ (tracked, with sources.json).
- Lot and centre renders: reference/lots, reference/centers (local, gitignored, regenerable).
