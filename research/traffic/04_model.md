# 4. The procedural method: drivers who read the road

## Principle (the user, 2026-10-01)

Drivers react to their environment, never to rules baked per road. A driver sees signs, bar
markings, signals, the centre line, junctions, crossings, other vehicles, trams, trains, people,
and the player, and applies Ohio's rules (01) to what it sees. To change a limit, change the
sign. To change a traffic pattern, change the markings and signs.

## Parts

| Part | File | Role |
|---|---|---|
| **TrafficSigns** | remake/characters/traffic_signs.gd | The world as drivers see it. Loaded from `road_furniture.json` (the data RoadFurniture draws) plus the road network's junctions; queried by position. Runtime edits: `add_sign`, `remove_sign`, `set_sign`. |
| **RoadDriver** | remake/characters/road_driver.gd | One driver: perception, rules, decisions, motion (IDM). Used by cars and by tram operators. |
| **NpcTraffic** | remake/characters/npc_traffic.gd | Gives each moving vehicle near the player a RoadDriver, with the real person's traits. Each frame it builds the shared picture of road users: vehicles, trams, trains, the player, pedestrians. |
| **TransitVehicle** | remake/scripts/transit/transit_vehicle.gd | Trams are driven by a professional RoadDriver toward their timetable position. They are held up by traffic and signs, catch up when clear, never run ahead, and stop at their stops. Trains keep their timetable on the rails. |
| **Generator traits** | npc_traits.json (layer L2, groups *conduct* and *driving*) | `self_control`, `sensation_seeking`, `driving_anger`, `deviance`, the `drive_*` weights, `record`. |

## A driver's frame

1. **Perceive**, 4 times a second, looking ahead 25–110 m depending on speed.
   - **Signs:** those whose face looks back at the driver (dot product with heading < −0.6), on
     the right or overhead, within 9 m of the path:
     - passing a `speed_N` sign sets the limit to N;
     - passing a `town` sign into town sets 40 km/h (Ohio 25 mph); passing the back of one out of
       town sets 90 km/h (55 mph);
     - warnings (`stop_ahead`, curves, junction, `rr_ahead`) lower the speed for the next 120 m;
     - a `stop` or `yield` sign gives a line: the stop bar across the driver's lane near the sign,
       or the sign itself.
   - **Bends:** the path's curvature ahead.
   - **Signals:** the signal ahead and its state for this approach. Opposite arms share a phase:
     22 s green, 4 s amber, 2 s all-red.
   - **Junctions and crossings:** junction nodes on the path, and rail crossings.
2. **Desired speed:**
   - the limit × (1 + `drive_speeding`);
   - capped by curves, √(a_lat / κ) braking back to the driver, with a_lat = 2.0 + 1.6 × sensation seeking (operators 1.4);
   - capped by warnings, and for trams by the timetable.
3. **Constraints**, each a gap and an obstacle speed:
   - **Stop sign (4511.43).** Decided once per sign: a full stop with probability `drive_full_stop`,
     +0.26 when people or traffic are about.
     - *Full stop:* stop at the line for at least 1 s, then go when the junction is clear (nobody in
       it or arriving within 4 s on another road). All-way stops go in arrival order.
     - *Rolling stop:* slow to 2.2 m/s and go, unless something is coming, in which case they stop
       after all. Logged as `rolling_stop`.
   - **Yield sign:** slow to 15 km/h; stop only if something is coming.
   - **Signal (4511.13).**
     - *Red:* stop at the line, 10 m before the centre.
     - *Amber:* stop if they can do so comfortably; with probability `drive_red_light` they go on.
     - *Fresh red, close:* `red_light` × 0.4 run it. Logged as `red_light`.
   - **Uncontrolled junction (4511.41 and .42).**
     - Yield to a vehicle from the right arriving within 3 s of themselves.
     - Turning left, wait while an oncoming vehicle is within 5 s.
   - **Rail crossing (4511.62):** stop 8 m short while a train is within 400 m.
   - **People (4511.46).**
     - Someone in the path within 18 m: everyone stops.
     - Someone at the road's edge ahead: stop with probability `drive_yield_peds`, else pass.
       Passing close is logged as `failed_to_yield_pedestrian`.
   - **Vehicle ahead (4511.34):** IDM with time headway `drive_headway`.
4. **Passing.**
   - **On the right (4511.28):** held behind a stopped vehicle for over 3 s, with probability
     `drive_pass_right`, they swing 2.6 m right and pass. Our streets have one lane each way, so
     this is the illegal kind. Logged as `passed_on_right`.
   - **On the left (4511.29–.31):** behind a slow vehicle (under 60% of their desired speed) for
     over 4 s, they overtake when nothing is coming within 220 m and no junction is within 30 m.
     Allowed where the centre line is dashed or absent, or under the half-speed exception.
     Across a double yellow only with probability `drive_cross_solid`, logged as
     `crossed_double_yellow`.
5. **Move:** the Intelligent Driver Model (Treiber, Hennecke & Helbing 2000):
   - acceleration a = a_max[1 − (v/v_des)⁴ − (s*/s)²];
   - desired gap s* = s₀ + vT + vΔv / (2√(a_max·b));
   - parameters: a_max = 1.3 + sensation seeking, b = 2.2, s₀ = 2 m, T = `drive_headway`;
   - lines are placed s₀ beyond the real line, so drivers stop at it.
6. **Speeding** is logged once per limit zone when a driver holds 8 km/h (5 mph) or more over the
   limit for 3 s.

## The weights (generator, layer L2)

| Trait | Built from | Calibrated to | Generated (n = 4,882, age 16+) |
|---|---|---|---|
| `self_control` | conscientiousness (0.5), agreeableness, calm; rises with age to 56; men −0.05 | Gottfredson & Hirschi | — |
| `sensation_seeking` | openness, extraversion; men +0.08, women −0.06; −0.009 per year from 30 | Zuckerman; Ball et al. 1984 | — |
| `driving_anger` | neuroticism, low agreeableness; falls with age | Deffenbacher; Lajunen & Parker | — |
| `deviance` | 0.62 × (1 − self-control) + 0.25 × sensation seeking + 0.15 × anger + low honesty | Junger et al. 2001 | median 0.17 |
| `drive_speeding` | 0.83 × (0.065 + 0.3·dev + 0.1·SS) + noise | NHTSA 2011 typology × Ohio 0.83: speeders 25%, sometime 33%, none 42% | 25% / 32% / 43%; 16–20: 55%; 65+: 9%; men 29%, women 20% |
| `drive_full_stop` | 0.27 − 1.3·dev + noise | 22.8% full stops (DeVeauuse et al.) | mean 0.28 |
| `drive_headway` | 1.45 − 0.9·anger − 0.6·SS + noise, s | ~10% under 1 s (estimate) | 9%; median 1.58 s |
| `drive_pass_right` | 0.06 + 0.6·dev + 0.25·anger | ~10% of chances (estimate) | mean 0.10 |
| `drive_red_light` | 0.02 + 0.3·dev + 0.1·SS | young, male, prior violations (Retting et al.) | mean 0.035 |
| `drive_yield_peds` | 0.53 − 1.0·dev + noise | 53 per 100 stopped for pedestrians (DeVeauuse et al.) | mean 0.52 |
| `drive_cross_solid` | 0.01 + 0.35·dev + 0.2·anger | (estimate) | mean 0.02 |
| `record` | base × e^(β·(dev − 0.17)) | felony 8% of adults (Shannon et al. 2017); traffic ~17% (NHTSA 2011); risky-driver odds ratios, violent 2.6, vandalism 2.5, property 1.5, traffic 5.3 (Junger et al.) | felony 8.9%, traffic tickets 15%; top-quartile odds ratios: violent 4.1, vandalism 2.4, property 2.2, traffic 6.0 |

The violent-record odds ratio overshoots Junger's 2.6 because the trait also makes violent
records commoner among men, who are higher in deviance; Junger controlled for sex. A future
pass could separate the two.

Python (`tools/charref/traits.py`) and the game (`NpcTraits`) produce identical values for the
same person, checked on four people.

## Not yet

- No turn-signal lamps.
- No emergency runs, so 4511.45 (pull over for lights and siren) has nothing to trigger it.
- No police presence, though the research says it raises compliance.
- The three signals keep fixed time and their lamps aren't drawn.
- Cars meeting at a junction are kept apart by the rules, not by collision.
- Runtime sign edits change behaviour at once, but the drawn sign changes only when
  road_furniture.json is rebuilt (tools/road_furniture.py).
