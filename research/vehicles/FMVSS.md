# FMVSS and the fleet's package rules

The user (2026-10-02): "I want the belt line to be higher on the other vehicles. Reference the FMVSS."
These are the Federal Motor Vehicle Safety Standards (49 CFR 571) and the bumper standard (49 CFR 581) behind the
fleet's class standards (`remake/blender/fleet/specs.py`, `remake/blender/kit/loft.py`). The station's people build
to them as heritage law. Numbers are quoted from the regulation or NHTSA where a source is given.

## The belt line

**No FMVSS sets a belt line height.** Three standards have pushed every modern car's belt line up and its side
glass down, and we follow that outcome:

| standard | what it requires | why the belt goes up |
|---|---|---|
| **FMVSS 214**, side impact protection | Door strength in a static crush test. A moving deformable barrier test (a striking vehicle at 48.3 km/h meeting a target at 24.2 km/h: 54 km/h closing, the barrier's wheels crabbed 27°). A 75° pole test | Side-door beams and a stiff sill-to-belt structure sit between the occupant and the striker. A higher belt gives the door more depth of structure |
| **FMVSS 226**, ejection mitigation | Applies to vehicles of 4,536 kg GVWR or less. Excludes walk-in vans, modified-roof vehicles, convertibles, and vehicles with no doors or easily removed doors. An impactor fired out through each side window, rows 1–3, may not move more than **100 mm** past the window's plane | The countermeasure, a side curtain air bag, must cover the daylight opening and **overlap the belt line** (the window's lower edge). Belt overlap, loft size and pressure account for about 75 % of a system's performance (NHTSA ESV paper 25-000428). Smaller, higher windows are easier to cover |
| **FMVSS 216a**, roof crush resistance | GVWR ≤ 2,722 kg: the roof holds **3.0×** the unloaded weight; 2,722–4,536 kg: **1.5×**. The plate may move at most **127 mm**, with no more than 222 N on a 50th-percentile head form | Strong pillars and rails: thicker A/B/C-pillars and a shallower glasshouse |

**Our rule.** The belt (the side glass's foot) is **0.42 m above the front H-point** on every new class. The Carrow
wagon, a 1970s design, has it at 0.20 m. Our floor is fixed by the boards (deck 0.50 + floor 0.05 = 0.55 m):

| class | H-point (front) | belt | belt − H |
|---|---|---|---|
| sedan, limousine, hearse | 0.85 | 1.27 | 0.42 |
| crossover, full-size SUV, pickup | 0.89 | 1.31 | 0.42 |
| coupe / convertible | 0.82 | 1.24 | 0.42 |
| van | 0.95 | 1.37 | 0.42 |
| heavy truck cab (cab over the wheels, floor 1.30) | 1.70 | 2.12 | 0.42 |
| school bus | 0.97 | 1.39 | 0.42 |
| *station wagon (SW180, unchanged)* | *0.85* | *1.05* | *0.20* |

The windscreen's foot meets the belt at the cowl (the A-pillar's line starts at the belt + 0.02). A bonnet falls
forward from there by each class's `hood_drop`. Headroom: H-point to headliner ≥ 1.13 m for our tallest people
(2.08 m; WAGON.md §2).

## Lamps: FMVSS 108

| lamp | where | ours |
|---|---|---|
| headlamps | centres **22–54 in (0.56–1.37 m)** above the ground; "as far apart as practicable", one each side at the same height | `head_lamp_z` per class, checked in `Builder.lamps()` (an assert) |
| tail and stop lamps | **15–72 in (0.38–1.83 m)**, one each side, as far apart as practicable | `tail_lamp_z`, checked |
| centre high-mounted stop lamp | on the centre line, high | over the hatch or back window, on a trunk's deck under the rear window, or high on a box's rear |
| side marker lamps | amber at the front, red at the rear; on wide vehicles **≥ 15 in (0.38 m)** up | on the fenders and quarters, or the cargo's rear corners |
| identification lamps | vehicles **80 in (2,032 mm) wide or more**: exactly three on the centre line, 6–12 in (150–300 mm) apart, amber at the front, red at the rear | on the van (2.12 m), the trucks (2.48 m) and the bus (2.48 m): 0.22 m apart |
| clearance lamps | the same vehicles: at the widest points, as high as practicable | at the roof's corners, or the box's rear top corners |
| school bus warning lamps | an eight-lamp system: red and amber, front and rear, high | the school bus's `warning_lamps` token |

## Bumpers: Part 581

Passenger cars' bumper face bars meet the pendulum's impact ridge in the bumper zone, **16–20 in (0.41–0.51 m)**.
Our cars' bumpers are centred at **0.45–0.50 m** (`bumper_z`); the trucks' at 0.52–0.60 m.

## Mirrors: FMVSS 111

A driver's-side outside mirror is required, and a passenger-side one on the vehicles where the inside mirror's view
is blocked. Every class gets both. School buses add **cross-view mirrors** on the front corners (S9), the
`crossview_mirrors` token.

## Buses: FMVSS 217, 220, 221, 222, 131

| standard | requirement | the school bus (BS300) |
|---|---|---|
| **217**, emergency exits | School bus rear emergency door: an opening that passes a box **1,145 mm high × 610 mm wide**. Side emergency door ≥ **1,140 × 610 mm**. Emergency windows pass an ellipsoid with **500 × 330 mm** axes. Roof exits ≥ **410 × 410 mm**. Other buses: **432 cm² per seating position** | Rear emergency door: twin leaves 0.80 m wide by 1.30 m high. Side windows 0.76 m long, belt to head 0.73 m. Two roof hatches 0.60 m square |
| **220**, rollover protection | **1.5×** the unloaded weight on the roof; the plate moves ≤ **130 mm** | A heavy frame (`"heavy": true`: 34 mm main tubes, a stiffer frame in the damage model) |
| **221**, body joint strength | Each panel joint holds at **60 %** of the weakest joined panel's tensile strength | (The detach rule's tolerances: panels stay on) |
| **222**, passenger seating | Seat spacing: about **20 in (508 mm)** from the seating reference point to the seat back ahead (21 in with tolerance) | Rows 0.71 m apart |
| **131**, pedestrian safety devices | A stop signal arm on the driver's (left) side | The `stop_arm` token |

## Glazing and the rest

FMVSS 205 (glazing materials: AS-1 laminated windscreens, AS-2 elsewhere) has no geometry in it. In the game, glass
shatters at the first strained fastening (tolerance 1.2 %). FMVSS 206 (door locks and retention) is why every door is
hinged at its front edge and sliding doors run rearward.

## Sources
- 49 CFR 571.226 (Cornell LII): applicability, exclusions, the 100 mm limit
- NHTSA ESV 25-000428: belt line overlap in ejection mitigation
- NHTSA / SAE (FMVSS 214 test descriptions): the MDB test speeds and crab angle
- FMVSS 216a (Federal Register 2009, NHTSA TP-216a): 3.0× / 1.5×, 127 mm, 222 N
- FMVSS 108 tables (via NTEA's lighting guide; Hawaii Admin. R. Exhibit A): mounting heights, identification and clearance lamps
- 49 CFR 571.217 (Cornell LII): school bus exit dimensions
- NHTSA interpretations and TP-220 / TP-221 / FMVSS 222: the roof load, joint strength and seat spacing
