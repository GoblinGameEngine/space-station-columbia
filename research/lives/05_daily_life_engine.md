# 5. The daily-life engine

## 1. Places: the contract, and the units
**The registry** (`npc_places.json`, doc in 01) describes place **types**, not instances. For
each type it holds:
- the shells that can host it;
- jobs by occupation;
- opening hours and days;
- visits: purpose, rate per person per week, who, and dwell time;
- whether it's a third place;
- its price level;
- demand per 1,000 residents;
- catalog signage hints;
- the addictions and roles it links to;
- **contents slots**: fixture categories, stock families, machinery and signage style.

The contents slots are the contract the models will be built to: engine first, then game bible,
then models.

**Units** (`bake_places.py` → `npc_place_index.json`, **901 units**) are what each building holds:
- a store's storefronts, one unit each, and its upper floor (offices, a lodge hall, hotel rooms,
  flats);
- a civic building's use; a works' use;
- a church, school, farm (at its barn), hotel, motel, stand.

**Fixed buildings** keep their type: a church is a church, and the cannery a cannery.

**Flexible units** (storefronts and upstairs offices) get their purpose **procedurally, per
settlement**:
1. each type's demand (`per1000`) is scaled to the town's flexible units;
2. about **8% are left vacant** (story hooks: who will open here?);
3. units are filled greedily, largest deficit first, with a bonus for the type the catalog's
   current signage suggests.

253 of 398 signage hints were kept. The rest were re-signed to what the town lacked. The story
can re-sign a shop later, since a purpose is only signage plus contents.

**Flats over shops:** 123 residence units (catalog `upper_use: apartments`) are now homes, with one
household each (`flat` in `npc_settlements.json`). Main streets have people living on them.

## 2. Anchors: everyone's places (`bake_lives.gd` → `npc_lives.json`)
For each of the **2,399 residents** (homes and flats; farm families live in the farmhouse, not in
the barn, silo or shed, which fixes an older bug), the bake draws the traits a day needs, then
assigns:
- **Work:**
  - first, every workplace gets someone to open it: the nearest free worker of one of its trades;
  - then the rest, in a hashed order, by occupation × posts × (posts left)² × exp(−distance /
    reach). The reach is 9 km with a car, 2.5 km without;
  - farm and fish-house families work their own place.
  
  Result: 1,339 workers, 0 unplaced, **95% of workplaces staffed**. The rest are mostly farms
  whose family is retired, and country churches that share a pastor.
- **School:** the nearest-ish school; university students go to the college (the largest school
  in the college town); 60% of preschoolers go to childcare.
- **A regular place for each purpose** they're eligible for (the visit's `who`), chosen by a Huff
  gravity model: exp(−d / reach) × personal liking (0.5–1.5) × 2.5 for their own town. The reach
  is 1 km with a car and 400 m without.
  
  Everyone has *their* grocery, café, barber and bar, and (if they attend) their church, mostly
  in their own town.

## 3. The day (NpcLife.stays / timeline, a pure function of person and day)
- **Work** by the occupation's `hours` column:

  | hours | time |
  |---|---|
  | day | 9–17 |
  | early | 6–14 |
  | evening | 16–24 |
  | shift | rotates weekly through 6–14, 14–22, 22–06 |
  | bartenders | 17–01 |

  - The hours are clamped to the workplace's opening hours, so there's no night shift at a
    school.
  - Personal habit shifts the start: conscientious people keep closer to the clock.
  - Days: weekday places Monday–Friday; others two days off in a row, the person's own; farms
    nearly every day.
  - Remote workers are at home about 65% of days.
- **School** 8–15:15 on weekdays; childcare 8–16:30; college classes in a daily block.
- **Worship**: Sunday 10:00–11:15 for weekly attenders, one Sunday in four for monthly.
- **Errands and leisure:** each regular purpose is drawn with probability (visits per week / 7),
  modified as follows:
  - × 3 when the place feeds one of the person's addictions;
  - × (0.4 + 1.2·extraversion) for third places;
  - × 1.4 on weekends for shops and leisure;
  - × 0.15 for children, except treats and outings.
  
  Each visit is placed in a free window within the opening hours (evening for drinks, films and
  meetings), for its dwell time.
- **Out of doors:** a stroll near home (more likely for retirees and extraverts), and children at
  play after school.
- **Trips** join the stays, with the mode for each trip (04). When a gap is long enough, they go
  home in between.

**The week, sampled** (800 people, `npc_life_test.gd`): away from home at 03:00 1%, 08:00 36%,
10:00–12:00 55–58%, 17:00 25%, 21:00 11%. Saturday midday 29%. Sunday 10:00 46% (church). A week's
stays: work 2,166; groceries 658; strolls 645; school 540; coffee 472; fuel 388; meals out 342;
drinks 304; worship 287. Deterministic (100/100 identical). 0.4 ms per person-day.

## 4. In the game (NpcPopulation)
Around the player, the candidates are the residents of nearby homes and flats, plus the **staff
and regulars of nearby places**. Each is shown if their day puts them in view:
- **on foot:** walking their route on the pavement. The game clock runs 30× faster than legs (an
  hour is two minutes), so a walk is visible from its scheduled start for as long as it really
  takes to walk: *the schedule says when they set off, their legs say how long it takes*;
- **by car or tram:** the door-to-kerb walk at either end;
- **strolling:** the older random walk from their door;
- **lingering:** at the bandstand, a food stand or a ride.

A per-person "next event" time skips everyone who is indoors until later, so a refresh costs about
8 ms. **Tested in game** (Harrow Falls main street, Monday):
- 08:30: 5–8 people out, walking to work, school, coffee, or home;
- 17:20: **19 out** (home 8, work 3, coffee 2, school 2, car service, pharmacy, groceries, a
  driver home).

"Where are you off to?" in conversation answers from their day: "Off to the café in Harrow Falls
-- coffee."

## 5. The `[LIFE]` prompt card (NpcLife.card)
This is added to the prompt from psychology 06 §8, after `[PERSON]`. An example:
```
[LIFE]  lives in a flat over a shop in Harrow Falls
        works as a shop clerk at the grocery in Harrow Falls (day hours)
        walks; has no car
        money: struggling
        regular places: groceries at the grocery in Harrow Falls, coffee at the café ..., drinks at the bar / tavern ...
        private struggles (never named unless trust is high): alcohol
        today: 09:05 work at the grocery in Harrow Falls; 18:40 drinks at the bar / tavern in Harrow Falls
        right now: on the way to the bar / tavern in Harrow Falls (walk)
```
Tokens: `LIFE.*`, `MONEY.*`, `ADDICT.*` and `FAITH.worship` in `research/psychology/tokens.json`.

## 6. Open items
- **Relationships** (L3) should add visits to friends' and family's homes. The registry has no
  "visit a friend" purpose yet.
- Bicycles, parked cars and tram stops are models the engine will expect (04).
- Transients (hotel guests, day-trippers: `transients` in `npc_settlements.json`) aren't scheduled
  yet.
- Shop interiors: the contents slots say what goes where. A per-unit contents plan (which fixtures
  on which wall) is the next contract, after the game bible.
- The refresh (~8 ms every half second) could be spread across frames.
