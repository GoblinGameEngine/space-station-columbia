# Great Lakes building research: changelog

- 2026-10-05: region opened. Codes, styles, compatibility and futures written. corpus.json (13 Commons buckets plus
  Lucas County assessor cards) and lot_samples.json (23 Wisconsin areas) defined.
- 2026-10-05: vocab.json gained the lot and boundary families (lot_w, lot_depth, lot_shape, lot_access, lot_corner,
  lot_coverage, rear_yard, outbuilding, lot_tenure, bound_front/side/rear), at the user's request to tokenize lots.
- 2026-10-05: `colour_trim:grey` added (GL-0024: grey strip-centre trim).
- 2026-10-05: off-target category pulls removed from the corpus (not buildings of the type, or out of scope):
  Leacock Museum garden tulips and an upstairs fireplace (Ontario Cottage category: a museum's interior and garden);
  Mariakyrkan, Gävle (a Swedish church in "Split-level houses"); Big Pink, Saugerties NY (a single famous house, not
  representative); a furniture-fixtures sale photo (big box); a sundae (fast food). Out-of-region Lustron and dollar-store
  photos are kept as national types (TOKENS rule), with their real places recorded.
- 2026-10-05: 42 buildings annotated (GL-0001..0042): the postwar, bungalow, town-house, apartment, Main Street, strip,
  roadside, prefab, Ontario and Toledo assessor-card sets.
- 2026-10-05: HC-019 (Selfridge Field quarters) skipped: no photographs in remake/reference (drawings only).
- 2026-10-05: HC-027 (Schwartz House) skipped: only interior photographs on file.
- 2026-10-05: HF-042 (Luce House) skipped: only a porch detail photo.
- 2026-10-05: HF-057 (Pinkerton House) skipped: only an avenue-of-trees photo, the house not visible.
- 2026-10-05: HVN-* (Montauk NY) excluded from the region: New York counts only for its Lake Erie / western shore. HVN-006 is a 3D render, not a photo.
- 2026-10-05: K-094 skipped: the photo shows only trees and a pier.
- 2026-10-05: K-018 skipped: its photo (a rural stone house) doesn't match the record (a commercial building in Tiffin): a catalog mismatch to check.
- 2026-10-05: vocabulary: added `form:grain_elevator` (a rail-side concrete or crib elevator: tall working house, headhouse, bins). Every Great Lakes farm town has one by the tracks, and no existing form fitted (K-024).
- 2026-10-05: HFW-010 tokenized at low confidence: its photo shows the St. Joseph pier and pierhead light, not the Coast Guard station. K-053's photo looks across Broadway at Gary's courthouse, not the municipal building. M-002 and M-035 use a later image (the first is an interior or a site plan).
- 2026-10-05: HC-027 (Schwartz House, Wright) skipped: its only photo is an interior.
- 2026-10-05: vocabulary: added `form:silo` and `form:round_barn` (farmstead structures the barn forms didn't cover) and `roof:dome` (silo caps, round-barn and civic domes).
- 2026-10-05: vocabulary: added `form:tower` (a free-standing tower: water towers and standpipes, lighthouses, lookouts). Every town has a water tower; the lakeshore has lights.
- 2026-10-05: catalog records left out of building tokens on purpose: crossings (bridges, culverts, rail crossings: CULVERT-*, MAJOR-*, RAIL-*, SMALL-*, XBR-*), docks, piers, wharves, boardwalks, decks and the breakwater (*-W*, *-D*). These are civil works, not buildings; the building vocabulary has no terms for them, and they belong to the road and waterfront generators, which have their own specs. Also skipped: HF-042, HF-057, K-094, HC-027 (no usable exterior photo) and K-018 (photo mismatch).
