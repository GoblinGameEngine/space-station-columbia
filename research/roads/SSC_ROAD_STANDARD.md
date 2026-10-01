# Space Station Columbia — Road Standard (SSC-RS 1)

The station's own rules, drawn from the research in this folder (markings.md, signs.md,
rail_crossings.md, cross_sections.md). The station was built by a North American consortium
with European engineers, so:
- **colours and sign shapes are North American**: yellow separates opposing traffic, red STOP
  octagon, yellow warning diamonds, green guide signs;
- **legends are symbol-first**, as in Canada and the Vienna Convention;
- **speeds are metric**;
- **line modules are the UK's**, which read better at the station's short sight lines.

Everything is placed by rule from each road's **class** and its **context** (how built-up the
place is). `tools/road_network.py` applies the rules; the game draws what it writes.

## 1. Context (local density)
For any point on a road, count the placed structures within 150 m:

| Context | Structures within 150 m | Typical place |
|---|---|---|
| **core** | 25 or more | downtowns, boardwalk fronts, harbour streets |
| **town** | 6–24, or inside a settlement footprint | residential streets, town edges |
| **rural** | fewer than 6 | farmland, section roads, the coast roads between towns |

## 2. Road classes and cross-sections
| Class | Width | Lanes | Town / core cross-section | Rural cross-section | Speed town / rural (km/h) |
|---|---|---|---|---|---|
| hwy (SR 14, US 30, Coast Hwy) | 12 m | 2 × 3.65 m + 2.35 m paved shoulders | curb and gutter | 2.4 m gravel shoulder each side | 60 / 90 |
| county | 8 m | 2 × 3.5 m | curb and gutter | 1.5 m gravel shoulder | 50 / 70 |
| main (town main streets) | 11 m | 2 × 3.5 m + parking | curb and gutter | (always in town) | 40 |
| street | 7 m | 2 × 3.5 m, no centre line | curb and gutter | 0.9 m gravel shoulder | 40 / 60 |
| gravel (section roads) | 6 m | unmarked | none (a soft edge) | 0.6 m gravel shoulder | 60 |
| alley | 3 m | one lane, concrete | none | — | 15 |

- **Curb and gutter** (town and core): a 0.45 m concrete gutter pan at road level along each
  edge, then a 0.15 m barrier curb.
- **Gravel shoulders** (rural): loose gravel, level with the road for the first half of the
  shoulder width, then falling 4 % to the verge.

## 3. Markings (white 0.10 m unless stated)
| Class | Centre | Edges | At junctions |
|---|---|---|---|
| hwy, rural | broken yellow 3 m mark / 6 m gap (passing permitted); solid double yellow for 60 m either side of a junction, rail crossing or bridge, and on bends sharper than 15° per 50 m | solid white 0.15 m, 0.3 m in from the paved edge | — |
| hwy, town / core | double solid yellow | none (curb) | stop line on the minor road |
| county, rural | broken yellow 3 m / 6 m; double solid yellow near junctions and bridges | solid white 0.10 m | stop line on the minor road |
| county, town / core | double solid yellow | none (curb) | stop line on the minor road |
| main | double solid yellow; parking edge line 2.2 m from each curb | none | stop lines, crosswalks |
| street | none | none | stop line where it meets main, county or hwy |
| gravel, alley | none | none | none |

- **Stop lines**: white, 0.4 m wide, across the approach lane, 1.2 m before any crosswalk
  (2 m back from the crossing road's edge if there is none).
- **Crosswalks**:

  | Context | Style |
  |---|---|
  | core | continental "zebra" bars 0.5 m wide, 0.5 m apart, 3 m long |
  | town | two transverse white lines 0.3 m wide, 3 m apart |
  | rural | none |

  They go across every approach at core and town junctions of main, county or hwy roads.
- **Road studs** (cat's eyes), rural hwy only: on the centre line every 18 m.
- **Rail crossings**: a stop line 4.5 m from the nearest rail. On paved approaches outside the
  core, an "RXR" marking 30 m before it.

## 4. Signs
Mounting:
- Signs stand on the right-hand verge, 0.6 m back from the curb (town) or 2 m from the edge
  (rural), on galvanised posts.
- Height to the bottom of the sign: 2.1 m in town, 1.5 m rural.

### Regulatory
- **STOP** (red octagon, 0.75 m): on the minor approach wherever a lower class meets a higher
  one (the order is alley < gravel < street < county < main < hwy), and on gravel roads at any
  paved road.
- **ALL-WAY STOP** (a STOP with an "ALL WAY" plate) where two roads of the same class meet in
  core context, or main meets county.
- **YIELD** (red and white inverted triangle): street meets street in town, on the approach
  with fewer structures along it.
- **Speed limit** (white rectangle, black numerals, km/h):
  - at every town entry, both ways;
  - after every junction where the limit changes;
  - repeated every 1.5 km on rural hwy and county roads.
- **Traffic signals** (three-aspect heads on mast arms, a 60 s cycle) where a hwy or county road
  meets a main street or a through street in core context, in towns of 100+ structures. They
  replace the STOP signs there.
- **Overlaps:** where a highway runs through a town on its main street, the two are one road. The
  higher class owns the stretch and its markings, and no junctions are counted along it.

### Warning (yellow diamond, 0.75 m)
- **Curve** (a bent arrow) 60 m before a bend of 35° or more within 80 m, on rural roads.
- **Junction ahead** (a symbol) 80 m before a STOP-controlled junction on a rural road.
- **Railway ahead**: a round yellow disc with a black X and "RR". 150 m before rural crossings,
  60 m before town and core ones.
- **Stop ahead**: 90 m before a STOP on a road rated 70 km/h or more.

### Guide (green, white legend)
- **Town entry**: the town's name and population, where a hwy or county road enters a
  settlement footprint.
- **Street name blades** (green, white capitals) at every core and town junction: the names of
  both roads, or the road's number where it is signed only by number.
- **Route markers**: white shields for the state routes (SR 14, US 30, Coast Hwy) at town exits
  and every 3 km.

## 5. Railway level crossings
Every crossing has the **SSC crossbuck**: a white X with a red border and black lettering, on
the right of each approach, with a "2 TRACKS" plate where needed. Protection rises with context
and road class (the research's common rule):

| Level | Where | What |
|---|---|---|
| **P — passive** | gravel and street roads in rural context | crossbuck and STOP sign; advance RR disc |
| **L — lights and bell** | county and street roads in town context; rural county roads | crossbuck mast with two pairs of flashing reds (alternating 1 Hz) and a bell; advance disc; stop line |
| **G — lights, bell and half barriers** | hwy anywhere; any road in core context; main streets | as L, plus a half barrier on each approach (red and white striped boom with 3 lamps, lowering in 10 s); countdown markers (3-2-1 bars, European style) on rural hwy approaches |

Crossing surfaces are concrete panels between and outside the rails, flush with the road.

## 6. Network rules
Applied by `tools/road_network.py`, called from `tools/map_expanded.py`.

1. **Every road end joins another road** at a real junction:
   - An end on or beside another road is run on to that road's centreline.
   - An end short of a road is carried on to it. It follows its own heading (a ray up to 320 m) or
     takes the nearest road within 60 m, if the way is clear of buildings, the sea, the great rivers
     and the lake.
2. **Creeks are bridged, not a reason to stop.** Section roads cross creeks; the bridge scan gives
   each crossing a small bridge or a culvert. They stop only at the sea, the lake, a harbour or a
   great river's basin. The great rivers are crossed only by the highway and county bridges.
3. **A section road never runs along a creek.** Its surveyed line jogs up to 65 m (as real
   section roads do) so that it crosses creeks instead of following them. Where a road met a
   **railway bridge** because it ran down the creek under it, it now crosses the rail on its own
   level crossing, clear of the rail bridge, and meets the creek on its own bridge. That was the
   road at s 17,170 m (RAIL-05); it now runs at s 17,215 m.
4. **Roads crossing the ring's seam** (s = 0 / 18,850 m) are one continuous road.
5. **Islands of road:** a group of roads cut off from the rest gets the shortest clear road to the
   nearest other road: a street if it's under 150 m, a county road otherwise. Victory Bay is a real
   island in Lake Tamsin and stays road-free; it's reached by water.
6. **The only dead ends** are turning circles: a town's cul-de-sacs, beach access roads past the
   coast road, and farm roads stopped by a great river's basin. Each gets a DEAD END sign 70 m back
   from the circle.

## 7. Grading
Applied by `tools/road_profile.py`; the research is in grading.md.

1. **Every road keeps within its class's maximum grade** (AASHTO / TxDOT Table 4-11, rolling
   terrain):
   - hwy 5 %, county 7 %, gravel 10 %, main 7 %, street and alley 8 %;
   - the railway 1.5 %.
   The profile is the closest fit to the ground that obeys the limit, found over the whole network
   at once. Where the ground has a bluff or a small cliff, the road is cut into it or built up on
   fill.
2. **Vertical curves** round every crest and sag over about 3 × the design speed.
3. **Junctions** have one height: roads within 3 m of each other are graded together.
4. **Small bridges are level**, at the higher approach's height, and the road ramps up to them
   within its grade. The great bridges climb from the graded road on each bank. Each approach
   starts on dry ground, never out in the river's basin.
5. **Side slopes** are cut and filled at 2:1 (up to 14 m wide).

## 8. Clearance
Applied by `remake/tools/placement.py`, `tools/road_profile.py` and `CoastalWalks.gd`.

1. **No building stands in a carriageway.** A building overlapping a road, plus 1 m, is moved
   straight back from that road until it clears. One with streets on several sides, which no move
   under 30 m clears, is left out.
2. **A crossing never stands in another road's way.** Of two crossings that overlap, the one on
   the greater road stays. A crossing whose model reaches within 1.25 m of another road's
   centreline is left out, and so is one on a great bridge's line. Their roads cross the creek on a
   buried culvert.
3. **Walks stop at the kerb.** A boardwalk, pier or rubble mound doesn't continue across a road's
   carriageway.
4. **Nothing grows through a bridge.** There are no trees under a great bridge's deck.
5. **Parked cars leave the middle clear.** Kerbside parking may narrow a lane, but a car can always
   pass down the middle. Boarding ramps are solid to people only.

## 9. Where roads meet bridges
Checked by `remake/tools/bridge_ends.gd`: at every end, the road's centreline must be within
0.5 m of the bridge's middle and within 3° of its axis, with no step over 5 cm.

1. **A great bridge follows the road it carries.** Its approaches run along that road's line, at
   least 30 m each end. The span runs straight between the road's points on the two banks. The
   line is rounded where the two meet. The deck starts level with the road's surface.
2. **A small bridge sits on its road.** Its deck's two ends are on the road's centreline, and the
   model is turned along the chord between them. A road that bends there is eased straight across
   the deck and its approach slabs, blending back over 15 m. A crossing at a road's very end, a
   bridge to nowhere, is left out.
3. **The road's surface stops at a small bridge.** The road ribbon, its kerbs, shoulders and
   markings end one row short of the deck, over the model's approach slab. The model carries the
   road across.
4. **Markings match.** A great bridge's deck has the road's double yellow centre line.



## 10. Sidewalks, parking, names and lots (2026-10-01)
Each road's cross-section is the law of the city its settlement follows. That law is in `research/law/02_cities.md` and is applied by `tools/street_rules.py`.

**Parking lanes**
- A parking lane is 2.4 m wide and widens its own side. The road's line runs down the middle of the travel lanes; each side is described by `hl` / `hr` and `park` [left, right].
- Parking is allowed where the city's ordinance allows it, and never where a travel lane would be left under 2.9 m. Our drivers keep to their own lanes, so there are no yield streets.
- On residential streets parking is on one side, the side with more doors. Downtown streets have parking on both sides.
- No parking within 9.2 m (30 ft) of a junction (ORC 4511.68). The parking-lane line stops there.
- No parking within 45.7 m (150 ft) either side of a tram stop, on both kerbs (the station's own rule; research/law 02_cities.md). No parking-lane line through the zone; R7-107 (NO PARKING, tram symbol) where each parked kerb meets it. Parked cars (place_ground_vehicles.gd) and NPC drivers (npc_traffic.gd) keep out of it through `TramStopZones`.

**Sidewalks**
- Sidewalks run behind the kerb on every town street.
- Downtown, the sidewalk runs from the kerb to the building face (3 m or more).
- On residential streets, a 1.2–1.5 m walk sits behind a 1.2–1.8 m tree lawn.
- Buildings clear the back of the walk (`placement.py`, measured by their footprint, not their awnings).

**Signs (research/law/04_signs.md)**
- Downtown: timed parking and a pay station every 60 m.
- NO PARKING every 60 m on unparked sides of town streets.
- EMERGENCY ROUTE or FLOOD ROUTE where the city has them.
- NO OUTLET and 40 km/h at each subdivision's mouth.
- A street-name blade at every town junction. `tools/street_names.py` names every town street: Main St, numbered streets, trees and families, and Drives and Courts in subdivisions.

**Lots (`tools/parking_lots.py`)**
- Each large city has a downtown lot behind the street wall, never at a corner.
- Each city and town of the two largest tiers has a park-and-ride lot at its park-and-ride tram stop (TransitNet).
- Stalls are 2.75 x 5.5 m with 7.3 m aisles; 1 accessible stall per 25.
- P at the entrance; PARK & RIDE 100 m out on the street.

**Pipeline (after map_expanded.py):** street_rules, placement, road_profile, road_profile again, town_grade (always after the last road_profile: it fits the town ground to the final profiles), the places bakes (make_places, bake_places, bake_paths, bake_lives), bake_transit.gd, street_rules, street_names, parking_lots, road_furniture, then place_ground_vehicles and place_aerostats. Then the world bakes.
