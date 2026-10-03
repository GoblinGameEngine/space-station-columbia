# The fleet's modular bodies

Every road vehicle type in the fleet (`remake/characters/npc_fleet.json`) is now built the way the Carrow wagon
was (MODULAR_VEHICLES.md):
- a skateboard board;
- a welded tube space frame;
- interior and exterior panels joined at every edge, the two shells joined at every opening, sealed by construction.

The 40 Grok-derived models were deleted (2026-10-02). The belt lines follow FMVSS (FMVSS.md), and every component is a
token (TOKENS.md).

## The pipeline

| step | file |
|---|---|
| the boards | `tools/vehicles/platforms.py` → `chassis/platforms.json`; `remake/blender/chassis/chassis.py` → `chassis/*.glb`. Added: **Harrow H-31** (3.1 m: full-size SUVs and pickups) and **Carrow K-36** (3.6 m: limousines and hearses) |
| a class standard from a spec | `remake/blender/kit/loft.py`: the loft (13-point half profile; front "hood" or "flat"; rear "hatch", "trunk" or "wall"; a high floor for cab-over cabs), the frame rings, slots, tops, damage settings |
| the specs, base styles and variants | `remake/blender/fleet/specs.py` |
| the builder | `remake/blender/fleet/builder.py`: panels (cells of the loft grid), interior, ends, reveals, closers, wells, underpan, dressing, equipment, cabin, cargo modules |
| the build | `flatpak run org.blender.Blender -b --factory-startup --python <abs remake/blender/fleet/build.py> -- <abs godot_project/remake/vehicles> <abs research/vehicles/fleet_img> [STD ...]` |
| the tests | `~/.venvs/ssc-assets/bin/python tools/fleet_test.py [type ...]`: both shells sealed, no tube in view, nothing across an opening |
| in the game | `FleetBodies` (the registry), `RemakeModularCar` (drivable; `RemakeWagon` is one), NPC traffic (`NpcTraffic` builds the board plus the `VehicleBody`), the Communicator's Summon app (Deliver any type) |

## The classes

| standard | class | board | types (base first) |
|---|---|---|---|
| SW180 | station wagon | Carrow K-28 | station_wagon (its own builder: `remake/blender/wagon/carrow_wagon.py`) |
| SD180 | sedan, 4 doors, trunk | Carrow K-28 | sedan, luxury_sedan, company_car, police_car, taxi, fire_chief_car |
| CU185 | crossover, 5 doors, hatch | Carrow K-28 | crossover_suv |
| FS200 | full-size SUV, 3 rows | Harrow H-31 | full_size_suv, police_suv |
| PU190 | crew-cab pickup + bed | Harrow H-31 | pickup_truck, public_works_pickup, tow_truck, utility_bucket_truck |
| CP165 | two-seat coupe | Solana L-25 | sports_car, convertible |
| LM220 | six-door limousine | Carrow K-36 | limousine |
| HR220 | hearse | Carrow K-36 | hearse |
| VN230 | forward-control van, sliding door, barn doors | Steward broad | delivery_van, parcel_van, service_van, paratransit_van, ambulance, hotel_shuttle, food_truck, ice_cream_truck, mail_truck (right-hand drive), armored_truck |
| HB250 … HX250 | cab-over truck (high floor) + cargo module | Steward heavy | box_truck, refrigerated_truck, garbage_truck, recycling_truck, dump_truck, fire_engine, ladder_truck, street_sweeper, milk_tanker, semi_truck |
| BS300 | school bus | Steward heavy | school_bus |

Not built: **city_car** and **minivan** (the pod and the van: their own hand-built models) and **surrey_bike** (a
pedal quadricycle, not a board vehicle).

## Lessons (to keep the next class fast)

- **Rings never on a jamb.** Set them 0.035 m into the pillar or post. Add a ring just inside each sloping pillar's
  top (the header − 0.02, the C-pillar's top + 0.02), so the cant rail runs level over the doors.
- **A C-pillar needs rings every 0.2 m**, and a foot ring whose head and cant joints sit under the deck's edge (as
  the cowl ring does at the windscreen's foot).
- **A trunk is outside the cabin:** its rings take the "no interior" branch exactly from the C-pillar's foot (no
  end-cavity margin).
- **The underpan's end pans must reach the board's risers.** The riser stations are added to the loft.
- **A high floor reorders the profile** (skirt, arch, sill). A cab-over door may sit over its arch; a low-floor door
  may not (asserted).
- **The tube test and the crossing test know every new role** (trunk_lid, leaf_trim, cargo_*, equipment).

## The rest of the vehicles (2026-10-02, the same day)

The user: "keep going with the rest of the vehicles". Every remaining type in `npc_vehicles.json` now has a modular
body, except the hand-built player rigs, which stay as they are: the pod (city_car), the van (minivan), the bicycle,
the personal aerostat and the Carrow tram.

| family | how it is built | types |
|---|---|---|
| more road types | the loft, and variants on it | unmarked_car, lifeguard / brush / hi-rail trucks, yard_tug, farm_pickup_flatbed (PF190), grain_truck (HK250), cement_mixer (HM250), mobile_crane (HC250), tram_maintenance_car (HW250), motorhome (MH300), transit_bus (TB300) and sightseeing_trolley |
| trailers | `TrailerLoft`: a cargo module only, on **Harrow running gear** (new boards harrow_tr25 / tr50 / ts150: rails, beam axles on leaf springs, a tongue or a kingpin) | utility, boat, camper, livestock, semi (dry, reefer), low loader |
| open light vehicles | a tub (the cargo bed machinery) on the new **Solana micro boards** (m20 / m16 / m12 / m10 / m06, their own lower deck); seats, controls, a cowl with its lamps, a canopy or cage (tubes shown on purpose) | golf_cart, utility_cart, hydroponics_harvest_cart, utv, parks_mower, riding_mower, atv, go_kart, bumper_car, mobility_scooter, power_wheelchair, skid_steer, forklift, kiddie_train |
| farm and site | the loft with `wheels_outside` (a narrow body between big wheels) on the new **Steward farm boards** (farm5 / farm7: r 0.62); cab-over heavies; implements on Harrow gear | utility / row-crop tractors, backhoe_loader, combine_harvester, crop_sprayer, grain_cart, hay_wagon, manure_spreader, hay_baler, planter_drill, plough_disc, excavator |
| rail | the loft (a high body over bogies) and cargo modules on the new **Steward rail boards** (standard gauge 1,435 mm, two-axle bogies) | passenger_train (the transit trains now build it), freight_locomotive, boxcar, covered_hopper, tank_car, flatcar, reefer_car |
| unpowered / single-track | token recipes, `remake/blender/fleet/parts.py`: no board, the frame shown | motorcycle, scooter_moped, child_bicycle, cargo_bike, adult_tricycle, kick_scooter, skateboard, surrey_bike, manual_wheelchair, rollator, baby_stroller, child_wagon, shopping_cart, hand_truck, pallet_jack, wheelbarrow, luggage_cart, housekeeping_cart, hospital_gurney, food_cart |
| boats | `remake/blender/fleet/hull.py`: a hull loft (keel, garboard, chine, topside, sheer, deck camber), a liner inside, the ribs (the frame) between, the deck's cockpit, a wheelhouse, the gear | rowboat, canoe, skiff, pedal boat, PWC, rescue board, sailboat, pontoon, cabin cruiser, lobster boat, coast guard, tug, trawler, ferry, barge |
| air and space | token recipes | cargo / rescue aerostat, passenger_shuttle, supply_freighter, eva_sled, cargo_mule, spoke_elevator_car, travel_lift |

Boats, the parts recipes and the air/space types are `prop` in the registry: the Summon app sets them down as bodies.
Floating, flying and pedalling them is the next step.

**Wheels never pass through the body** (the user: "absolutely needs to be corrected").
- `fleet_test.py --wheels` tests every tyre against every component of the body except its wheel wells and underpan.
  A front wheel is swept through its 35° steering lock; a 2 cm margin applies.
- A low cargo module's wheels get housings: open below, clear of the tyre (and of its steering sweep) by 6 cm. The
  floor is notched round them and the lining is holed to the housing's top.
- A seat over a wheel housing sits up on it.
- A body between its wheels (a tractor) is narrow enough for their sweep.
- In the game a modular vehicle rides on its **board's** wheel radius, not the type's spec radius (0.34 m for
  nearly all of them: a tractor's 0.62 m wheels sank 28 cm into the road).

**Open tubs show their frame** (the user: "visible external tub frames are okay on the boat trailer, atv, and similar
vehicles"). A cargo-only body with an open bed, dump body or deck, and every open light vehicle, carries `frame_shown`
in its standard. The tube test skips it; the seal, crossing and wheel tests still apply. An enclosed body still hides
every tube.

- A tub narrower than its board sits on the board's deck: no sill pan out to the deck's edge (it stood in a steered
  tyre's path), and the frame's foot stands on the deck, not under it.
- The tests take the board's deck at its own height (`deck_top_m`; the micro boards' decks are lower than 0.49 m), and
  a `no_arch` body has no arch openings to cross.

The superseded Grok-made models of every rebuilt type (96 models and their textures, the old tram's among them) were
deleted. Only the hand-built pod, van, bicycle and personal aerostat remain at `remake/vehicles/`. The transit train
builds only the modular coach.

## The full fleet test, and what it found (2026-10-02, late)

Run over all 134 types, the four checks found these. Each is now a rule.

- **A blank window's lining is its own interior token** (`pane_lining_*`, lining_bay). It had been part of the
  exterior pane, so every panel van's cargo area leaked through its blind windows.
- **A cab-over cab's inner sill meets its floor.** The lining stopped 2 cm above the floor (a slot). The floor's
  interior cells run out to the sill.
- **A bonded windscreen has a black frit** (`screen_frit`, a trim token): a 10 cm band inside the glass along its
  sides, deeper at its foot. It hides the A-pillar tube where the pillar narrows to nothing at the screen's foot.
- **A cargo plinth has a belly pan.** Ladder-frame boards (trailers, rail cars) have no deck, and no board has one
  past its end.
- **The ring joining cab and cargo** sits in the cargo front wall's cavity (3 cm behind the face), no larger than
  the cab's outline at its tail. On the face, or ahead of it, its tubes showed.
- **The cargo keel** runs in the board's deck on the board, and in the floor slab past its end.
- **A cargo door's hole is cut only in the walls it is on.** A caravan's one-sided door left the other wall open.
  A low wall's doors start at the sill row, and a cargo door records its own sill and head in the blueprint.
- **A box's belt rail runs over its arches**, as a bed's does. A wheel housing's outer wall closes the wall cavity
  where the lip dips between tandem wheels.
- **Micro boards get proportionate arches**: 8 cm of clearance over the tyre, not a car's 21 cm.
- **Mirrors mount ahead of the door**, never on the leaf: a mirror is a fixed token and the door swings away.
- **Open beds show their frame** like open tubs (`frame_shown_y`: only that stretch; the cab's frame must hide).
- **Boats:** frames follow the hull as drawn (straight between stations); a true V bottom keeps the floor brace in
  the cavity; in a cockpit the deck's joints drop into the side deck; the frames' depth grows with the boat
  (4 to 12 cm).
- A bug found on the way: the stop-arm branch had merged into the destination sign's, so every bus or shuttle
  with a sign also carried a school bus's stop arm.
