# Road grading: maximum grades, vertical curves, cut and fill (2026-09-28)

What US practice says about a road's longitudinal profile, and what Space Station Columbia's roads
(SSC-RS 1 §7, applied by `tools/road_profile.py`) take from it.

## Maximum grades
The AASHTO Green Book (*A Policy on Geometric Design of Highways and Streets*) sets maximum grades
by functional class, rural or urban context, terrain (level, rolling, mountainous) and design
speed. State manuals reproduce it. TxDOT's Roadway Design Manual, Table 4-11, gives these values
(percent, by design speed in mph):

| Context | Class | Terrain | 15–30 mph | 35–45 mph | 50–60 mph |
|---|---|---|---|---|---|
| Rural town, suburban, urban | Local | all | 8 | 8 | — |
| | Collector | level | 9 | 9–8 | 7–6 |
| | Collector | rolling | 12–11 | 10–9 | 8–7 |
| | Arterial | level | 8–6 | 6–5 | — |
| | Arterial | rolling | 9–7 | 7–6 | — |
| Rural | Local | level | 9–7 | 7 | 6–5 |
| | Local | rolling | 12–10 | 10–9 | 8–6 |
| | Collector | level | 7 | 7–6 | 6–5 |
| | Collector | rolling | 10–9 | 8–7 | 7–6 |
| | Arterial | level | 5–4 | 3 | 3 |
| | Arterial | rolling | 6–5 | 4 | 4 |

- "The maximum grades shown may be increased by 1% where there are one-way downgrades that are
  less than 500 ft in length."
- The maximum is to be used "infrequently rather than as a value to be used in most cases".
- Terrain classes: level is surrounding slopes of 0–8 %; mountainous is over 15 %. The Green Book
  itself allows urban local streets up to 15 % where the terrain demands it. The station's floor is
  rolling farmland and river bluffs, so we use rolling.

**Minimum grade** (drainage): 0.5 % beside unpaved ditches, 0.3 % on curbed pavement.

## Vertical curves
Where two grades meet, the change is spread over a parabolic vertical curve of length L = K·A,
where A is the algebraic difference in grade (%) and K comes from the stopping sight distance at
the design speed.
- TxDOT Table 4-12 (Green Book 3-34 / 3-36): crest K runs from 3 at 15 mph to 384 at 80 mph; sag
  K from 10 to 240.
- The preferred minimum length is **3 × the design speed** (L in ft, speed in mph), though that is
  not a design control.
- No curve is needed where the grade changes by ≤ 1 % (design speed ≤ 45 mph) or ≤ 0.5 % (faster).

## Railways
Mainline ruling grades are usually 1–1.5 % (AREMA practice). Grades steeper than about 2.2 % are
rare outside mountain lines.

## Cut and fill slopes
Where a road is graded above or below the ground, the side slopes are commonly 2:1 (horizontal to
vertical) at the steepest, and flatter where there's room.

## What SSC-RS 1 §7 takes
| Class | Treated as | Design speed | Max grade | Vertical curve (≈ 3 × speed) |
|---|---|---|---|---|
| hwy | rural arterial, rolling | 55 mph | **5 %** | 50 m |
| county | rural collector, rolling | 45 mph | **7 %** | 41 m |
| gravel | rural local, rolling | 30 mph | **10 %** | 27 m |
| main | urban arterial, rolling | 30 mph | **7 %** | 27 m |
| street | urban local | 25 mph | **8 %** | 23 m |
| alley | urban local | 15 mph | **8 %** | 14 m |
| rail | mainline railway | 60 mph | **1.5 %** | 55 m |

How it's applied (`tools/road_profile.py`):
- Heights are the best fit to the terrain that keeps every grade within its class maximum, over
  the whole network at once, so a junction has one height.
- Crests and sags are rounded over the vertical-curve length.
- Small bridges are level decks. Each sits at the height of its higher approach, and the road ramps
  to it within its grade.
- The ground is cut and filled to the road at 2:1, widening up to 14 m past the shoulder (MapTerrain).
- On the current map the largest cut or fill is 6.4 m; the mean is 0.28 m.

## Sources
- TxDOT Roadway Design Manual 4.8.1, Grades (Table 4-11): https://www.txdot.gov/manuals/des/rdw/chapter-4--basic-design-criteria/4-8-vertical-alignment/4-8-1-grades.html
- TxDOT Roadway Design Manual 4.8, Vertical Alignment (minimum grades, K values, curve lengths): https://www.txdot.gov/manuals/des/rdw/chapter-4--basic-design-criteria/4-8-vertical-alignment.html
- Kentucky Highway Knowledge Portal, Roadway Grade: https://kp.uky.edu/knowledge-portal/articles/roadway-grade/
- MoDOT EPG 230.2 Vertical Alignment (Green Book Tables 3-34, 3-36): https://epg.modot.org/index.php/230.2_Vertical_Alignment
- AASHTO Green Book: https://www.aashtostandards.com/product/AASHTO-Green-Book-GDHS-5/
