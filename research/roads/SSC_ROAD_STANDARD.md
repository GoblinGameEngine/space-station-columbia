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
