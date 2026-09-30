# 9. Affinity: how people feel about each other and about the player

The user asked (2026-09-30) for **affinity to be tracked toward the player and between characters**. The player builds their own mythos through the people they meet.
This page covers the priors the bible supplies, how they combine, and what's stored. The psychology framework (`research/psychology/06`) owns the opinion tokens; these are their starting points.

## 1. The prior between two characters, A(i to j) in [-1, 1]
Every term is computed from generated or stored facts, so nothing needs storing until someone does something:
- **kin:** same household +0.45; parent or child +0.5; sibling +0.4; grandparent +0.35; cousin +0.15; share-kin (a child of my gifted share) +0.3;
- **lineage:** same lineage +0.08; the lineages' feud value (for example Moriarty and Castellanos -0.6); alliance +0.2 (lineages.json);
- **factions:** the faction affinity table below, x 0.5 per pair of memberships (factions.json);
- **settlement:** same town +0.05; rival towns -0.3; allied towns +0.2; plus the region term (North Shore v. South Shore -0.15);
- **faith:** same faith +0.1 (x 1.5 when both attend weekly); the faith affinity table;
- **familiarity:** same workplace +0.15; same regular place +0.05 per shared place (NpcLife anchors); neighbours +0.05;
- **temperament:** + 0.2 x (i's agreeableness - 0.5); - 0.1 when i is high in neuroticism and j is a stranger;
- **reputation:** + 0.1 x j's reputation valence if i knows of j (fame, and the knowledge the propagation engine delivers).

## 2. Toward the player
The player starts as a **stranger from somewhere else aboard**. The user chooses the home town, and the AI adapts.
- The prior is the settlement term for the player's chosen town against each character's, plus the region term. A Port Carrow player in Solana Point starts at about -0.3 with keen Suns fans.
- The first impression comes from dress, manner and the first line, via the psychology framework's appraisal.
- After that, only events move it: deeds witnessed or heard of through propagation, gifts, promises, insults.

## 3. What's stored
- **Sparse deltas only:** (i, j) maps to a list of {delta, cause (event token), day, decay}. The prior is always recomputed.
- **Decay:** small kindnesses and slights fade (half-life about 60 days); betrayals, rescues and deaths don't.
- **Scope:** deltas are stored for anyone the player has touched directly, or at one to three hops through propagation.
- **Between characters:** deltas are stored only when an event involves both, such as a feud started by the player's meddling. Everyone else runs on priors.
- **Size:** tens of bytes per pair touched. A long game touches a few thousand pairs.

## 4. The player's mythos
The player's own history is the story engine's chronicle (story 04 §2.9): a list of arcs, each with roles, beats and mythos.
Affinity is the quantitative side of that chronicle. Together they are the player's standing in each town, family and faction, and the NPCs quote it back.

## Faction affinity (priors)
| faction | faction | value |
|---|---|---|
| charter_league | open_hand | -0.35 |
| charter_league | waymakers_assembly | -0.20 |
| charter_league | wardens_circle | -0.40 |
| charter_league | homeward | -0.60 |
| charter_league | grange | +0.30 |
| charter_league | daughters_of_the_launch | +0.40 |
| charter_league | marshals | +0.35 |
| open_hand | waymakers_assembly | +0.25 |
| open_hand | wardens_circle | +0.35 |
| open_hand | cannery_union | +0.20 |
| open_hand | marshals | -0.10 |
| open_hand | homeward | -0.30 |
| waymakers_assembly | wardens_circle | +0.15 |
| waymakers_assembly | homeward | -0.40 |
| wardens_circle | marshals | -0.30 |
| cannery_union | grange | +0.15 |
| cannery_union | marshals | -0.15 |
| order_of_the_lamp | daughters_of_the_launch | +0.30 |
| order_of_the_lamp | cannery_union | +0.15 |
| mariners_faithful | suns_nation | -0.45 |
| heritage_hedwig | order_of_the_lamp | +0.30 |
| heritage_cote | heritage_hedwig | +0.20 |
| heritage_sociedad | suns_nation | +0.30 |
| heritage_hedwig | mariners_faithful | +0.30 |
| heritage_cote | mariners_faithful | +0.30 |
| aerostat_guild | marshals | -0.10 |
| homeward | marshals | -0.50 |

## Factions

- **the Charter League** (political, about 34.0% of adults): the Balance as it is; leave the Undercroft closed; the Quiet Clause kept; order and thrift; strong in kessler, marlowe, oceanview, tamarack, countryside, victory_bay; leaders Rosalind Achterberg-Nuñez
- **the Open Hand** (political, about 31.0% of adults): freer gifting of shares; an inquiry into the Undercroft; petition the Steward; answer the Notice; strong in bellhaven, solana_point, port_carrow, cedar_ford, brightwater; leaders Tobias Wainwright-Okafor
- **the Northland Grange** (guild, about 5.0% of adults): farmers first; fair prices at the Chutes; the Northland Fair; strong in marlowe, loomis_grove, dunmore_crossing, fenwick, countryside, tamarack; leaders Gunnar Lindqvist-Brandt
- **the Cannery and Dock Workers Union** (guild, about 4.0% of adults): jobs on the water; never forget Tern Harbor; no locked doors; strong in pelican_cove, tern_harbor, port_carrow, solana_point; leaders Rosa Pham-Moriarty
- **the Order of the Lamp** (club, about 7.0% of adults): charity; the Friday fish fry; a good Return for every member; strong in port_carrow, harrow_falls, fenwick; leaders Frankie Wisniewski
- **the Daughters and Sons of the Launch** (club, about 2.0% of adults): founder descent; the Launch Day rites; keeping the old stories; strong in port_carrow, kessler, victory_bay; leaders Beatriz Holloway-Anand
- **the Waymakers** (faith, about 6.0% of adults): the voyage is the pilgrimage; the Notice is a sign; ask where we're going; strong in bellhaven, oceanview, cedar_ford, solana_point; leaders Evangeline Mbeki-Hart, Tobit Asante-Grey
- **the Wardens' Library circle** (society, about 0.4% of adults, secret): learn how the station works; find Imogen; open the Undercroft; strong in bellhaven, kessler; leaders Caspian Holloway
- **the Homeward (Returner remnant)** (society, about 0.2% of adults, secret): Earth is home; the Green Message was true; the Steward stole the vote; strong in marlowe, countryside, tern_harbor; leaders -
- **the Aerostat Pilots' Guild** (guild, about 0.6% of adults): the air is free; racing; safety rules (after VY 438); strong in harrow_falls, solana_point; leaders Kasimir Horvath
- **the Mariners Faithful** (fans, about 15.0% of adults): the Port Carrow Mariners; strong in port_carrow, haven_point, tern_harbor, brightwater; leaders Ezekiel Brannock
- **Suns Nation** (fans, about 16.0% of adults): the Solana Point Suns; strong in solana_point, playa_verde, pelican_cove, oceanview; leaders Dante Okonkwo-Silva
- **the Hedwig Hill Polish Society** (heritage, about 2.0% of adults): Pączki Day; Dyngus Day; polka; strong in port_carrow, fenwick, harrow_falls; leaders Frankie Wisniewski
- **the Côte Society** (heritage, about 1.5% of adults): Carrow French; Saint-Jean-Baptiste Day; tourtière; strong in port_carrow, tern_harbor; leaders Colette Marchand
- **la Sociedad Solano** (heritage, about 5.0% of adults): Lake Spanish; the Fiesta de Rosario; Día de Muertos / Return Night; strong in playa_verde, solana_point, pelican_cove; leaders Itzel Solano-Garza
- **the Marshals Service** (institution, about 0.4% of adults): order; rescue; the Charter; strong in kessler; leaders Obadiah Kincaid-Morales

## Faith affinity

- catholic / lakes_union: +0.10
- catholic / full_gospel: -0.05
- full_gospel / waymakers: -0.35
- catholic / waymakers: -0.15
- lakes_union / waymakers: -0.10
- none / full_gospel: -0.15
- none / waymakers: +0.05
- freedom_baptist / full_gospel: +0.10
- plain / none: -0.10
- muslim / jewish: +0.10
- muslim / catholic: +0.05

## Regions

- north_shore / south_shore: -0.15
- northland / southland: -0.05
- kettle_valley / northland: +0.10
- kettle_valley / southland: +0.10
- north_shore / northland: +0.05
- south_shore / southland: +0.05
