# Waterfronts: boardwalks, piers, boat launches, yacht clubs (research, 2026-10-07)

The user, 2026-10-07: "look up boardwalk layouts and placement on the beach. Look up the number of stairs and entrances as
well as their placement. Look up piers and see what amenities they have ... how they are arranged. Find piers of the size
needed and catalog and tokenize the examples. Do the same for boat launches and yacht clubs along the great lakes, San
Diego and New England. Scale the yacht clubs to the metro area they are near."

The data is in `catalog.json`: 18 piers and wharves, 8 boardwalks, 6 launch records and 14 yacht clubs, all tokenised.
Earlier pier and boardwalk notes are in `research/coastal_communities/boardwalks_and_piers.md`. This page gives the
rules the generator uses.

## 1. Boardwalks and promenades on the beach

**Where they sit.**
- A boardwalk runs parallel to the shore at the back of the beach: on the dune crest, on a seawall, or just behind the
  last dune.
- Its distance to the waterline is the beach's width:
  - Pacific Beach and Mission Beach: 30–80 m;
  - Santa Cruz and Ocean City NJ: about 60–150 m;
  - Wildwood: 150–300 m at low tide (the widest on the East Coast).
- The town's first street, or a row of hotels and businesses, fronts it on the land side.

**Which kind, by region.**

| Region | Kind | Models |
|---|---|---|
| California | Concrete promenade on a low seawall | Mission/Pacific Beach's Ocean Front Walk; the Strand, with walkers above and a bike path on the sand below; Santa Cruz's Beach Boardwalk |
| New England resorts | Short timber boardwalk or promenade with a pleasure pier | Old Orchard Beach |
| Jersey-style resort (our Brightwater) | Timber planks on piles, 1–4 m above the sand | Atlantic City (planks on a concrete and steel frame); Coney Island (4.1 m above the sea, on concrete piles) |
| Great Lakes | Boardwalk along the harbour channel, from downtown out to the beach and the pier | Grand Haven |

**Width.**
- Big resorts: 18–24 m (Atlantic City 18.3 m, Coney Island 24.4 m).
- Towns: 6–12 m (Ocean City NJ builds 12 × 42 ft sections).
- Villages: 3–6 m.
- For us: cities 14 m, towns 9 m, villages 4 m.

**Stairs and entrances: how many, and where.**
- Stairs down to the beach at every street end, about one per block, every 90–120 m.
- Ramps up from the street at the main streets.
- ADA ramps onto the sand roughly every 5–6 blocks (500–700 m). Ocean City NJ has them at 1st, 6th and 12th Streets
  and between 34th and 59th. Wildwood has them at every few avenues, plus a beach taxi.
- Hard-packed beach mats lead out from the ramps.
- Comfort stations (restrooms, showers, a small lot and the main lifeguard tower) at the foot of the main streets,
  about every 1 km (Pacific Beach).
- Where there's no boardwalk, dune walkovers run perpendicular to the shore, 1.2–1.8 m wide, elevated on posts. They end
  at the dune's seaward toe, no more than 3 m past the vegetation, and their posts are sunk at least 1.5 m (Florida DEP).

**What lines it.** Hotels, arcades, food stands (pizza, fries, taffy, ice cream), surf and souvenir shops, bars,
bike and surrey rentals, a bandshell, and the pier's foot.

## 2. Piers: amenities and arrangement

Every pier we looked at is laid out in the same four zones, foot to head:

| Zone | What's there (tokens) | Examples |
|---|---|---|
| **foot** (shore end) | entry plaza or arch; lifeguard headquarters or tower; restrooms; bait and tackle; a restaurant flanking the base; an amphitheatre or bandshell; sometimes the train station | Huntington (230-seat plaza amphitheatre), San Clemente (Fisherman's Restaurant either side, the rail stop, the clock-tower Marine Safety building), Santa Monica (the Looff Hippodrome carousel) |
| **neck** | benches; lamp standards every 15–20 m; fishing rails both sides; shade and windbreaks; on wide piers, shops and stands in a row | Old Orchard Beach (souvenir shops), Santa Cruz (cars and parking) |
| **mid** | an octagonal or square platform with a shelter; bait shop; cafe and mini-mart; fish-cleaning station | Huntington (three octagons), Oceanside (bait shop), Ocean Beach (cafe and mini-mart) |
| **head** | a restaurant or diner (often a landmark on its own); a T or diamond fishing platform; an aquarium; a nightclub or ballroom; a light | Huntington (a diamond 33 m across with a 23 m-tall restaurant), Balboa (Ruby's), Manhattan (the octagonal Roundhouse aquarium), Old Orchard (a nightclub; once the 5,000-dancer Pier Casino) |

**Structure.**
- Deck 5–9 m above the water: Huntington 9.1 m, Redondo 7.6 m; typical fishing piers 1.5 m above high water.
- Width 6–12 m, widening to 9–30 m at the head. Amusement piers are much wider: Santa Monica is 92 m.
- Timber piles, or concrete piles and deck.
- New England wharves are broad timber or concrete platforms carrying shingle sheds, fish houses and bait dealers, with
  boats berthed along both sides: Gloucester's state fish pier is 305 × 107 m with two 46 m bays; Custom House Wharf
  has 1,128 m of dock edge.

**Sizes for our towns.** These come from the catalog, matched by town size and character:

| Town | Pier | Models |
|---|---|---|
| Solana Point | 420 m pleasure pier, octagon platforms, diner at a diamond head | Huntington, San Clemente, Pismo |
| Oceanview | 300 m municipal wharf with cars, restaurants and a fish market | Santa Cruz wharf at about a third the size |
| Playa Verde | 380 m fishing pier, T head, bait and cafe at mid-pier | Ocean Beach, Pismo |
| Harrow Falls (lake) | 330 m promenade pier (programme in coastal_communities) | Grand Haven's catwalk pierhead light on the breakwater |
| Port Carrow | Wharves: 5–7 at 60–160 m, the fish pier 180 × 60 m, Custom House Wharf | Portland ME, Gloucester |
| Brightwater (New England resort) | 150 m pleasure pier lined with shops, a nightclub at the head | Old Orchard Beach |
| Villages | A town wharf 40–80 m with a float | Edgartown, Stonington |

## 3. Boat launches

**The design standard** (Pennsylvania Fish and Boat Commission, Virginia DWR, Alaska, California Parks, Michigan DNR):

| Item | Standard |
|---|---|
| Ramp slope above the water | 12–15% |
| Ramp slope below the water | 15–20% |
| Lane width | 3.7–4.3 m each |
| Courtesy docks | L-head floats along the ramp; both sides of a double lane |
| Car-and-trailer stalls | 30–40 per lane, each about 3.0 × 12.2 m |
| Support area | about 0.26 ha per lane |
| Also | Restrooms; a staging and tie-down strip at the top of the ramp |

**Examples:**
- **Shelter Island, San Diego:** 4+ lanes, boarding floats, a large trailer-only lot, restrooms.
- **New Bedford Harbor (MA):** 2 lanes, 30 stalls. **Clarks Cove:** 1 lane, 22 stalls.
- **Grand Haven, Harbor Island:** 2 lanes, a lot expanded in 1998–2002, restrooms.

**Scaling for us:**

| Town size | Lanes | Stalls |
|---|---|---|
| City | 3–4 | 90–140 |
| Town | 2 | 50–70 |
| Village | 1 | 20–30 |

## 4. Yacht clubs, scaled to the metro

The measured clubs:

| Club | Metro | Town | Members | Slips | Note |
|---|---|---|---|---|---|
| San Diego YC | 3.3 M | | 5,000 | 600 | 200 dry; America's Cup |
| Southwestern YC | 3.3 M | | 900 | 385 | |
| Coronado YC | 3.3 M | 22 k | 950 | 264 | |
| Santa Barbara YC | 450 k | 88 k | 750 | | beach clubhouse |
| Ventura YC | 850 k | 110 k | 250 | 86 | |
| Chicago YC | 9.6 M | | 1,400 | | two stations |
| Bayview YC, Detroit | 4.3 M | | 1,000 | | 743 m² clubhouse, banquets for 250 |
| Macatawa Bay YC | ~120 k | Holland 34 k | | 75 | pool, restaurant, store |
| Grand Traverse YC | ~150 k | Traverse City 15 k | | | members' ramp, juniors |
| Ludington YC | | 7.7 k | | 40 | dining room, bar, decks |
| South Haven YC | | 4.3 k | | 35 | fuel and pumpout, bar |
| Camden YC | | 5 k | | moorings | 1912 Shingle Style clubhouse, NRHP |
| Portland YC | 550 k | 68 k | | moorings | a former summer cottage |
| Eastern YC, Marblehead | Boston | 20 k | | | 1881 clubhouse, pool, tennis |
| Lake Champlain YC | | | | | 257 m² clubhouse, 418 m² with patios |

**The scaling rule.**
- Members are about 0.2–0.3% of a working city's population, up to 1–2% for a resort or summer town (Camden,
  Marblehead, South Haven), with a floor of about 80.
- Slips run about 0.25–0.35 per member for a marina club (Ventura 0.34, Coronado 0.28) and none for a mooring club
  (New England).
- Clubhouse area is about 120 m² plus 0.7 m² per member (Bayview 743 m² for 1,000 members; Lake Champlain 257 m²).

**Our clubs** (resort towns use the summer-town factor):

| Club | Members | Slips or moorings | Clubhouse | Style |
|---|---|---|---|---|
| Solana Point YC | ~230 | ~75 slips | ~280 m² | Spanish, harbour |
| Harrow Falls YC | ~200 | ~65 slips | ~260 m² | Great Lakes; Macatawa / Ludington |
| Port Carrow YC | ~180 | ~60 moorings, launch service | ~250 m² | New England Shingle Style; Camden / Portland |
| Oceanview Sailing Club | ~120 | ~35 slips | ~200 m² | |
| Port Tamsin YC | ~110 | ~35 slips | ~190 m² | summer resort; South Haven |
| Brightwater YC | ~100 | ~30 moorings | | Shingle Style |
| Haven Point YC | ~80 | ~25 | | Coast Guard neighbour |

Every club has:
- a clubhouse with a dining room, bar and deck facing the water;
- docks with slips, or a mooring field with a launch landing;
- a dinghy dock;
- dry sail storage for small boats;
- a junior sailing shed;
- a flagpole with a yardarm;
- a fuel and pumpout float at the bigger clubs.

## Amenity tokens

`restaurant`, `diner`, `cafe`, `bar`, `nightclub`, `bait_tackle`, `fish_market`, `fish_cleaning`, `mini_mart`, `gift_shop`,
`souvenir_shops`, `candy_shop`, `ice_cream`, `food_stands`, `arcade`, `carousel`, `amusement_park`, `aquarium`, `museum`,
`exhibit_hall`, `amphitheatre`, `bandshell`, `lifeguard_tower`, `lifeguard_hq`, `restrooms`, `showers`, `benches`,
`lamps`, `fishing_rail`, `shelter`, `octagon_platform`, `T_arms`, `diamond_head`, `parking_on_deck`, `train_station`,
`hotel_cottages`, `lighthouse`, `catwalk`, `berths`, `floating_marina`, `ferry_landing`, `shanties_as_shops`, `freezers`,
`seafood_processing`

## Sources

- Boardwalks:
  - Ocean City NJ: https://downbeach.com/local/ocean-city-boardwalk-undergoing-42-million-facelif/ ; https://whyy.org/articles/jersey-shore-beach-accessibility-wheelchairs-mats-parking-ramps/ ; https://ocnj.us/accessibility
  - Wildwood: https://ablenews.com/sand-sea-and-wheels-a-winning-combination-in-the-wildwoods/ ; https://seachestmotel.com/guide-wildwood-crest-beaches/
  - Coney Island: https://en.wikipedia.org/wiki/Riegelmann_Boardwalk
  - Mission and Pacific Beach: https://www.traillink.com/gdbkpdf/trail/8714339/mission-beach-pacific-beach-boardwalk63922612202743-2026.pdf ; https://www.sandiegoreader.com/places/pacific-beach-boardwalk/
  - The Strand: https://www.timeout.com/los-angeles/sports-and-fitness/the-strand
  - Dune walkovers: https://floridadep.gov/sites/default/files/Beach%20and%20Dune%20Walkover%20Guidelines_0.pdf
- Piers:
  - Santa Cruz wharf: https://www.santacruzca.gov/Government/City-Departments/Parks-Recreation/Santa-Cruz-Wharf/About ; https://localwiki.org/santacruz/Municipal_Wharf
  - Stearns Wharf: https://legacy.geog.ucsb.edu/stearns-wharf-santa-barbaras-most-visited-landmark/
  - Huntington: https://en.wikipedia.org/wiki/Huntington_Beach_Pier
  - Oceanside: https://en.wikipedia.org/wiki/Oceanside_Pier
  - San Clemente: https://www.orangecountyoutdoors.com/get-out-there/piers/san-clemente-pier
  - Crystal Pier: https://sandiegomagazine.com/guides/vintage-crystal-pier/
  - Ocean Beach: https://oceanbeachsandiego.com/attractions/ocean-beach-pier
  - Manhattan Beach: https://en.wikipedia.org/wiki/Manhattan_Beach_Pier
  - Balboa: https://en.wikipedia.org/wiki/Balboa_Pier
  - Santa Monica: https://en.wikipedia.org/wiki/Santa_Monica_Pier
  - Redondo: https://en.wikipedia.org/wiki/Redondo_Beach_pier
  - Old Orchard Beach: https://en.wikipedia.org/wiki/Old_Orchard_Beach,_Maine
  - Gloucester: https://archives.obs-us.com/obs/adventur/gloucester/about/water/fish.htm
  - Custom House Wharf: https://en.wikipedia.org/wiki/Custom_House_Wharf
  - Nantucket: https://nantucketpreservation.org/?p=7132
  - Grand Haven: https://en.wikipedia.org/wiki/Piers_and_Revetments_at_Grand_Haven,_Michigan
  - South Haven: https://sah-archipedia.org/node/15365
  - Fishing-pier design: https://www.corada.com/documents/2012-tas/1005-fishing-piers-and-platforms
- Launches:
  - https://www.fishandboat.com:443/About-Us/Grants/Documents/BasicBoatLaunchDesign.pdf
  - https://dwr.virginia.gov/boating/building-boat-ramps/
  - https://www.hainesalaska.gov/media/18771
  - https://www.michigan.gov/documents/dnr/Final_Study_Phase_Report_Sep_2019_686709_7.pdf
  - https://www.portofsandiego.org/visit-waterfront/coming-going/boating/boat-launching-ramps
  - https://www.mass.gov/info-details/massgis-data-office-of-fishing-and-boating-access-sites
  - https://grandhaven.org/downloads/city-parks/harbor_island.pdf
- Yacht clubs:
  - San Diego YC: https://en.wikipedia.org/wiki/San_Diego_Yacht_Club
  - Southwestern YC: https://marinas.com/view/marina/ywcy7z_Southwestern_Yacht_Club_San_Diego_CA_United_States
  - Coronado YC: https://scya.org/?p=10958 ; https://ceqanet.lci.ca.gov/1989062105/2
  - Santa Barbara YC: https://scya.org/santa-barbara-yacht-club-sbyc/
  - Ventura YC: https://scya.org/project/ventura-yacht-club-vyc/
  - Chicago YC: https://en.wikipedia.org/wiki/Chicago_Yacht_Club
  - Bayview YC: https://en.wikipedia.org/wiki/Bayview_Yacht_Club ; https://www.dbusiness.com/daily-news/bayview-yacht-club-in-detroit-opens-5m-clubhouse-renovation-in-june/
  - Macatawa Bay YC: https://marinas.com/view/marina/95c1mw_Macatawa_Bay_Yacht_Club_Macatawa_MI_United_States
  - Grand Traverse YC: https://howsyourriver.com/access_sites/grand-traverse-yacht-club
  - Ludington YC: https://explore.predictwind.com/marinas/united-states/michigan/ludington-yacht-club
  - South Haven YC: https://southhaven.org/directory/south-haven-yacht-club
  - Camden YC: https://en.wikipedia.org/wiki/Camden_Yacht_Club
  - Portland YC: https://en.wikipedia.org/wiki/Portland_Yacht_Club
  - Eastern YC: https://en.wikipedia.org/wiki/Eastern_Yacht_Club
  - Clubhouse sizes: https://soundingsonline.com/news/stonington-yacht-club-finds-a-home/ ; https://d7.lcyc.info/node/214
