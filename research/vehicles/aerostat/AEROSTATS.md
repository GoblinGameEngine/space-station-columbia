# Aerostats, spacecraft and the spoke elevator (2026-10-04)

The last placeholder recipes in the fleet (fleet/parts.py: an envelope lathe and four slab fins over a box) are
replaced by bodies built to the fleet's rules (research/vehicles/MODULAR_VEHICLES.md, FLEET_BODIES.md).

## How they are built

- **The crew and passenger space is an ordinary fleet body**: `kit/loft.py` + `fleet/builder.py` -- the tube frame,
  exterior and interior shells joined at every opening by reveals, doors as closers, seats, the 2.2 m
  floor-to-headliner rule. The same tests apply (`tools/fleet_test.py`: seal, tubes, crossings, wheels).
- **It sits on a Steward keel** (`tools/vehicles/platforms.py` `keel()`): the Steward's spans and caps with no pods,
  and a pair of landing skids on sprung legs (`chassis.py` `steward_skid`). Keels: `steward_keel7` (the elevator car),
  `steward_keel8` (rescue gondola, freighter and mule cockpits), `steward_keel10` (cargo gondola), `steward_keel36`
  (the shuttle's fuselage).
- **What makes it fly is equipment**, each its own component: `fleet/aero.py` (envelope, fins, ducted fans and their
  pylons or booms, suspension struts and mast, the cargo saddle, sling frame and A-legs, the winch, the red cross,
  beacons and foot lamps, the boarding ladder) and `fleet/space.py` (wings with heat-tiled undersides, the tail fin,
  manoeuvring pods, main engine bells, landing gear, cargo pods and their spine, the drive section, thruster pods,
  manipulator arms, the dorsal fin, nose lamps, the elevator's rail trucks, guide shoes, rim lamps and finial).
- **Loft additions**: `tuck` (the lower side curving in below the belt: a rounded gondola; the sill joint follows the
  curve), `plan: "round"` (a circle in plan, ends floored at `round_min`: the elevator car), `pillar_inset`.
- **Smooth normals** (`kit/components.py`): a module with `smooth` set writes vertex normals, kept flat where faces
  meet at more than 40 degrees. The envelope and the fan ducts use it; everything else stays faceted.
- **Envelope livery**: stripes are at constant elevation round the hull (so they meet at the nose and tail), bands at
  constant t; every stripe edge is a row of vertices, so a stripe narrower than a facet never vanishes.

## The types

| type | standard | size | references |
|---|---|---|---|
| rescue_aerostat | AR700 `steward_mercy` | 16 m envelope (R 2.5), 6.9 m gondola, 4 fans | reference/grok/rescue_aerostat |
| cargo_aerostat | AC820 `steward_burden` | 34 m envelope (R 4.7), 8.2 m gondola under a saddle, sling frame 8.4 x 15 m on A-legs | reference/grok/cargo_aerostat |
| passenger_shuttle | SP300 `steward_skylark` | 29 m fuselage, 18 m span, 48 seats + 2 | reference/grok/passenger_shuttle |
| supply_freighter | SF600 `steward_packhorse` | 6.8 m cockpit, 6 bays of 2 x 3 pods, the drive (about 34 m) | reference/grok/supply_freighter |
| cargo_mule | SM450 `steward_mule` | 6.6 m tug, 4 thruster pods, 2 arms | reference/grok/cargo_mule |
| spoke_elevator_car | EE600 `steward_ascender` | round cabin 5.8 m across, benches, standing room | reference/grok/spoke_elevator_car |
| eva_sled, travel_lift | recipes (parts.py) | open machines: their frames show by design | reference/grok/eva_sled, travel_lift |

The Grok views disagree with each other on scale; the sizes were set from the 2.2 m rule (the gondola's height) and
the side elevations' proportions.

## In the game

- The aerostats fly: `RemakeFleetAerostat` (remake/scripts/vehicles/fleet_aerostat.gd) is a RemakeAirVehicle whose
  model is the keel and whose body is the fleet body; hull = gondola boxes (doorways open, boarding steps), spheres
  along the envelope, the sling frame's rails (the cargo aerostat lands on them: registry `ground` -3.12). Fan markers
  become the rig's engines. Its doors are `FleetClosers` (the road fleet's closers, now shared).
- The spacecraft and the elevator car are set down as their bodies (registry `prop`), as the boats are.
- Tested 2026-10-04: the rescue aerostat summoned, boarded, climbed to 200 m and held; the cargo aerostat stood on
  its frame; every spacecraft summoned without errors.

## Open

- The personal aerostat is modular since 2026-10-05: AP460 `steward_errand` on `steward_keel5` -- a spherical balloon
  (`shape: sphere`), four ducted lift fans on arms (`fan_axis: z`, mount `arm`), struts and a mast; the summoned one is
  the red variant `summoned_aerostat`. RemakeAerostat is a RemakeFleetCraft of it (the map's aerostats and the summoned
  one alike). Fans have the role "engine": separate meshes, each on a pivot the flight rig tilts (all fleet aerostats).
- The winch's cable is drawn stowed; the game doesn't pay it out yet.
- Spacecraft have no flight (they are for the port, which has no buildings yet).
