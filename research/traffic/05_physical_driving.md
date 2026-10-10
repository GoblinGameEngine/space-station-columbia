# 05: Physical driving (2026-10-09)

The user, 2026-10-09: "Their cars need to use driving physics and follow the roads and obey the road signs."

Before this, every NPC car was a frozen box slid along its route by `RoadDriver`. The rules worked, but nothing
physical held them to them: cars passed through each other and through cars parked across a corner, and never hit
anything.

## What it is now
- **Near the player** (within `NpcTraffic.PHYS_R` = 90 m, back to rails past 110 m), a driven car is a
  `VehicleBody3D` (`NpcCarBody`).
  - The engine's native raycast vehicle provides four sprung wheels at 1.6 Hz, tyre friction (mu 1.1), engine force and
    brakes.
  - The station's gravity and the air's drag are applied by hand.
- **The driver** (`RoadDriver`) still decides everything: signs, signals, junctions, the car ahead, Ohio's rules and
  each driver's own traits.
- **The chauffeur** (`NpcCarBody._chauffeur`) turns the driver's decided acceleration into engine force (within the
  type's torque and power) or brake. It steers with Stanley's controller: the heading error, plus the cross-track error
  at the front axle over the speed, toward the route offset by the driver's lane (passing, pulling over).
- **Where the car is along its route** is read back from the physics (`NpcTraffic._project`) whenever the driver
  decides.
- **Far off**, the car is frozen and placed on the route as before, because nobody can see it.

## Problems found on the way, and their fixes
- **Pure pursuit cut every corner.** A van turning into 121th St climbed the car parked on it. Stanley tracks the line
  itself.
- **The routes had spikes and loops.** Offsetting a polyline into its lane leaves a swallowtail inside every turn and a
  spike back on itself. A car on rails jumped through them unseen; a car on wheels went off the road.
  - `NpcTraffic.drivable()` cuts the loops, drops the spikes, and rounds every corner into an arc of up to 7 m.
  - The distances along the route, including the stops on a round, are scaled to the new length.
- **Corners came too fast.** `RoadDriver` sampled the route's bends every 6 m from 5 m ahead, so the corner just ahead
  was missed. It now samples every 3 m from 1 m ahead, over a 4 m window. The chauffeur also slows a car that is on
  full lock and still off its line.
- **Parked cars stood in junctions and lanes.** That was never seen with nothing solid. Now:
  - parking spots keep 13 m from a junction's middle (4511.68: 20 ft from a crosswalk);
  - parking lanes too narrow to clear the travel lane send the car off the street;
  - parked cars are agents of kind `parked`. They are only ever a possible leader, and a driver goes round one standing
    in the lane on the left, when clear (4511.31(A)(3)).
- **A last word before a collision** (`NpcTraffic._blocked_ahead`): anything right ahead of the car's nose, the way it
  is really pointing, within its stopping distance, puts the brakes on. Two cars stood nose to nose for 3 s let the
  lower id go first, slowly.
- **Creeping queues.** Physical speed jitter (0.02–0.3 m/s) meant a queued car never counted as stood still, so it
  re-decided every frame and the standoff rule never fired. Now a crawl under 0.15 m/s counts as stopped, and the brake
  holds below an acceleration of 0.3 m/s².
- **The first version did the tyres in GDScript**, as `RemakeGroundVehicle` does for the player's car. It cost
  0.12 ms per car per tick; at a rush hour 29 cars sent the frame rate into a spiral. The native `VehicleBody3D` costs
  about 1.4 ms a frame for all of them.

## Measured (Solana Point, Steam Deck, editor build)
| | Lane error, median of each car's worst | Over 2 m | Crashes |
|---|---|---|---|
| First cut (pure pursuit, raw routes) | 0.58 m | 13 of 62 cars | 6 in 45 s |
| Stanley + drivable routes + finer bends | 0.38 m | 0 | 1 |
| `VehicleBody3D` + the last word | 0.04–0.11 m | 0–1 (passing) | 0 in several minutes |

The frame rate at a rush hour (around 9:30, 60 moving) is 22–27 fps with physical driving, the same as with every car
on rails at the same moment. The rest of that frame is the population and the clocked traffic lookups.

## Also in this pass
- **Getting into parked cars:** use a parked traffic car (`NpcCarBody.interact`) and `NpcTraffic.take_over` stands the
  full drivable body of its type in its place (group `taken_vehicle`) with the player at the wheel. The traffic forgets
  it (`_gone`).
- **PDA, Edit > Dismiss Current Vehicle:** the vehicle you're in, else the nearest within 10 m (a map aerostat, a
  parked car, a traffic car at the kerb), else the summoned one. A parked one is gone for good (`VehicleStreamer.forget`,
  `NpcTraffic.forget`).

## From one place to another (later the same day)
The user: "NPC cars need to be driving with physics not moving arbitrarily ... They need to be going from one place to
another."
- **Setting off:** a car parked at the kerb when its trip begins drives out of its space (`_depart_leg`). If it points
  the route's way, it goes ahead and out into the lane; otherwise it makes a U-turn (radius 3.6 m) first. Before this,
  it appeared on the road at the trip's start.
- **Arriving:** at the far end the driver takes a free space on the kerb facing the way they arrive
  (`_find_spot(door, want_face)`). The route is cut 14 m short of it and runs into it (`_arrive_leg`, joined only on the
  space's own street). `RoadDriver.stop_at_end` brings the car to a stop at the end, and it is parked exactly where it
  stopped, with no snap to the space.
- **Bend-speed guard** (`RoadDriver.bend_speed`, checked by the chauffeur 10 times a second): no faster than the
  route's bends ahead allow. A car is handed to the physics no faster than that either. Without it, a car taken over
  at timetable speed just before a corner went through the corner.
- **Parking brake:** a stood car is frozen until its driver goes. `VehicleBody3D` creeps sideways down a camber at
  about 5 cm a second even when braked.
- **Bumps are not crashes:** a jolt only ends a drive when the car was doing more than 2.5 m/s.
- **The player's parked fleet** (pods, vans, bicycles) counts as obstacles.
- **Loop cuts:** `drivable()` only cuts loops under 15 m. A long route that really crosses itself had a block cut out
  of it, and the car drove a parallel street.

Measured: brakes give −5.9 m/s² for −6 asked; acceleration 2.1 for 2.0.

## The roads report themselves
The user: "Have the NPCs report to you misplaced road signs and malfunctioning road layouts. This way we can allow
the game to run on it's own and playtest itself."

`TrafficReports` saves to `user://traffic_reports.json`. Reports of the same kind within 10 m are counted together,
with the town, the road and who saw it. The kinds:

| Kind | Reported when |
|---|---|
| `sign_no_junction` | a stop or yield sign faces traffic with no junction within 30 m |
| `sign_in_lane` | a sign stands in the lane being driven |
| `sign_hit` | a vehicle knocks a sign down |
| `turn_too_tight` | a route's turn is under 2.6 m radius after rounding |
| `no_route` | no road route links two places a trip joins |
| `off_route` | a car is more than 3 m off its route for 2 s |
| `stuck` | a car stands 60 s wanting to go, with what holds it noted |
| `crash_static` | a car is driven into a building, pole or rail |
| `no_parking` | there is nowhere legal to park near a door |

`TrafficSelfTest` (`godot4 --path . -- --selftest [--quit-after-tour]`) tours every town at rush hours: the town hall
and then the grocery or tram stop, two minutes each. It logs each stop's crashes, trips and frame rate.
`tools/traffic_reports.py` reads the results.
