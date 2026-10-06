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
