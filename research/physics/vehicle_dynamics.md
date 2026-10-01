# Vehicle dynamics, impacts and ragdolls (2026-10-01)

What the remake's vehicles, people and signs do physically, the numbers behind it, and where the
numbers come from. The earlier survey (`vehicle_physics.md`: BeamNG, Forza, GT, GTA, RCAR) is
the background; this note covers what was built from it.

The aim is GTA-style play on top of physics that are close to real. The real part (masses,
power, torque, tyre grip, rolling resistance, drag, suspension, road roughness) sets how things
feel and how they relate to each other: a pickup is heavier and slower to turn than a hatchback,
grass is slower than asphalt, and a tram doesn't notice a bicycle. A small set of assists, listed
below, keeps the vehicles easy and fun to drive.

## Specs: every vehicle has mass, power and torque

`tools/places/make_vehicles.py` writes a `phys` block for every vehicle type into
`npc_vehicles.json`:

```
{mass_kg, power_kw, torque_nm, gear, wheel_r, top_kmh, drive (FWD/RWD/AWD), cda, source}
```

- **Named types** (`PHYS_AS`) use approximate specs of a real electric equivalent. All vehicles
  are electric (game bible). Examples:

  | type | kg | kW | Nm | top km/h | drive | CdA m² |
  |---|---|---|---|---|---|---|
  | city car | 1250 | 80 | 250 | 130 | FWD | 0.62 |
  | sedan | 1650 | 150 | 360 | 175 | RWD | 0.55 |
  | pickup | 2900 | 340 | 1000 | 170 | AWD | 1.15 |
  | sports car | 1600 | 380 | 650 | 250 | RWD | 0.50 |
  | box truck | 8000 | 220 | 1200 | 105 | RWD | 4.5 |
  | bicycle | 15 | 0.2 (rider) | 60 | 35 | RWD | 0.5 |
  | tram (per vehicle) | 40000 | 360 | 6000 | — | — | — |

- **Everything else** is scaled from its envelope size and its category (`PHYS_CAT`: density in
  kg/m³, W/kg, top speed, drive and Cd).
- **Gear** is set so the motor's top rpm (15,000 for cars, 6,000 for heavy vehicles) reaches the
  vehicle's top speed.
- **To change a vehicle**, edit its row and rerun `make_vehicles.py`. Driven vehicles read the
  block through `RemakeGroundVehicle.spec` (for example `"city_car"`), and NPC traffic uses it for
  the mass of each car body.

**Motor model** (single-speed EV): F = min(T·gear/r, P/v), with power reduced up to 60 % by
damage. **Drag**: ½·ρ·CdA·v² with ρ = 1.2.

## Suspension and tyres

- **Suspension:** a ray per wheel feeds a spring-damper.
  - Spring rate k = m_corner·(2π·f)², with ride frequency f = 1.4 Hz (cars; 2.5 Hz for the
    bicycle).
  - Damping c = 2ζ√(k·m), with ζ = 0.38.
  - A bump stop acts at the end of travel.
  - These are typical passenger-car values (Gillespie, *Fundamentals of Vehicle Dynamics*, ch. 5–6).
- **Tyres:** a simplified Pacejka curve, Fy = −μ·Fz·sin(1.4·atan(9α)).
  - A friction circle shares the grip between driving or braking and cornering.
  - Rolling resistance is crr·Fz.
- **Centre of mass:** a custom COM low in the body.
- **Gravity:** the station's spin gravity applies to the body (`StationGeo.gravity_at`).

## Surfaces: off-road is bumpy and slower

`RoadSurface` (`remake/scripts/vehicles/road_surface.gd`) looks up the surface under each wheel:
the road class from `terrain.json`'s roads, otherwise the landcover.

| surface | μ | crr | ISO 8608 class |
|---|---|---|---|
| asphalt (hwy/main/county) | 0.90 | 0.013 | A |
| street / alley | 0.88 | 0.014 | B |
| gravel | 0.60 | 0.025 | D |
| dirt | 0.55 | 0.05 | D |
| lawn | 0.45 | 0.06 | D |
| meadow | 0.45 | 0.08 | E |
| field (ploughed) | 0.50 | 0.15 | E |
| woods | 0.45 | 0.10 | F |

**Sources:**
- μ and crr: Wong, *Theory of Ground Vehicles*, rolling-resistance and adhesion tables, and
  Gillespie.
- Roughness: ISO 8608. The displacement PSD Gd(n0) at n0 = 0.1 cycles/m is 16·10⁻⁶ m³ for
  class A and quadruples per class (A 16, B 64, C 256, D 1024, E 4096, F 16384 ·10⁻⁶).

**Bumps:** the profile is synthesized as 30 plane waves with wavelengths from 1 to 25 m and
amplitudes √(2·Gd·(n/n0)⁻²·Δn), with fixed phases. The road is therefore the same every time you
drive it (deterministic and local).

**How much bumpier and slower?** Drivers on rough unpaved roads choose speeds that keep the RMS
vertical acceleration near 0.25 g on long runs and 0.4 g on short ones (Renfroe, Roberts & Partain
2002, SAE 2002-01-0805). That is the target the classes were checked against.

Measured in game with the city car, starting from rest at full throttle for 11 s with no
steering and obstacles ignored:

| surface | speed after 11 s | RMS vertical accel |
|---|---|---|
| asphalt | 109 km/h | 0.03 g |
| lawn | 74–82 km/h | 0.09–0.11 g |
| meadow | 53 km/h | (one run crossed a ditch) |
| field | 60–62 km/h | 0.15–0.19 g |
| woods | 60 km/h | 0.36 g |

Off-road is about 25–50 % slower over the same time. In the woods at 60 km/h the ride is already
past the 0.25 g comfort level, so going faster there is uncomfortable, as it would be in reality.

## GTA-style assists

The assists are kept small, and each one is labelled `play:` in the code.

- **Grip:** ×1.15 over real tyres.
- **Yaw damping** when not steering (0.8·m) and **anti-roll** torque (1.5·m), so cars don't spin
  or roll on their own.
- **Handbrake:** rear lateral grip ×0.35, for handbrake turns.
- **Air control:** steering and throttle pitch while airborne.
- **Self-righting:** a vehicle left upside down below 2 m/s for 2 s is put back on its wheels.
- **Bicycle self-balance:** the bike leans into turns at the lean angle that balances the turn,
  atan(v·ω/g).

## Impacts

**Damage** is detected from delta-V: the change in velocity within one physics step, beyond what
the forces explain. Thresholds follow RCAR low-speed crash tests:
- the crash sound plays from 10 km/h;
- damage starts at 15 km/h and scales with energy;
- 60 km/h is a write-off.

Damage reduces power (up to −60 %) and at 1.0 disables the vehicle.

**Vehicles the player drives** are RigidBody3Ds, so they collide with everything on layer 1, the
hulls and people.

**NPC traffic** (`NpcCarBody`) are kinematic boxes with their type's size and mass while their
driver controls them.
- When hit at a closing speed above 1 m/s, they exchange momentum along the line between the two
  vehicles: a 1D collision with restitution 0.2 (cars crumple rather than bounce).
- The NPC car then becomes a dynamic wreck under the station's gravity, and its driver is out of
  the traffic simulation.

**Station gravity** (`StationGravity`) is an Area3D around the player. Its point gravity pushes
away from the axis, so wrecks, ragdolls and signs fall toward the floor.

## People: ragdolls

`NpcRagdoll` gives each pedestrian a sensor capsule.
- **Trigger:** a vehicle or flying body entering the capsule at more than 1.5 m/s knocks them down.
- **Body:** 12 PhysicalBone3D segments, each with its share of the person's weight from Dempster's
  segment masses. The person's weight comes from their character sheet.
  - Hips 14.2 %, spine 13.9 %, chest 21.6 %, head 8.1 %, upper arm 2.8 %, forearm 2.2 %,
    thigh 10 %, shank 6.1 %.
  - Knees and elbows are hinges; the other joints are cones.
- **Momentum:** the body takes v·1.2·m/(m+w), with lift on the torso, head and arms (the wrap
  trajectory of real pedestrian impacts). The vehicle loses the same momentum.
- **Getting up:** they lie 2, 8 or 15 s depending on impact speed (<7, <14 or ≥14 m/s), then get
  up where they came to rest.
- **Tally:** the count is kept in `RoadDriver.tally.people_knocked_down`.

## Signs

`SignPhysics` puts sensors on the posts of signs within 90 m of the player.
- **Trigger:** a vehicle passing through above 1.5 m/s knocks the sign down.
- **Removal:** the sign is taken out of RoadFurniture's merged meshes and out of TrafficSigns, so
  drivers stop obeying a stop sign once it has been knocked down.
- **Physics:** the sign becomes a 25 kg body (a breakaway post and its plate) carrying its share of
  the momentum.
- **Limit:** at most 40 knocked-down signs lie around at once.

## Masses of everything that moves

| what | mass | how it moves |
|---|---|---|
| driven cars and vans | from `phys`, plus 80 kg per seated person | rigid body, raycast suspension |
| parked bicycles | 15 kg | rigid body (self-balancing when ridden) |
| NPC cars | from `phys` | kinematic while driven, dynamic once hit |
| pedestrians | weight from their character sheet | ragdoll when hit |
| signs | 25 kg | dynamic once knocked down |
| trams and trains | 40 t per vehicle | kinematic on their lines; they push, nothing pushes them |
| aerostats | kinematic | flown |

## Streaming: what's loaded

- **Parked cars, bicycles and aerostats** are `VehicleStreamer` records. A vehicle is built within
  its near radius (cars 120 m, aerostats 700 m) and freed beyond its far radius unless it is in
  use. Records that aren't built are drawn as impostors in one MultiMesh.
- **NPC traffic** always has bodies and colliders (physics positions and collisions, no
  rendering). Their models load asynchronously only when in the camera's view or within 25 m, and
  are freed after 3 s out of sight.
- **Traffic, transit, bridges and transit lines** wait until the world has loaded: bridges build
  one per frame, and transit lines are cached in `user://transit_lines.bin`.
- **Load time** dropped from about 50 s to about 20 s.

## Open

- NPC cyclists don't have a bike body yet. A hit knocks the rider down, and the bike is put away
  when they get up.
- Ragdolls jitter a little on GodotPhysics; Jolt (built into Godot 4.4+) is worth trying.
