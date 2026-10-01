# Vehicle interiors: how each was made

Written by `tools/assets/interiors_note.py` from the build logs. The user's call (2026-09-30): interiors are **extrapolated** from the exterior references where Grok made no interior views; any we don't like go back to Grok (`grok_refs.py <id> --views interior_section,interior_plan,interior_aisle,interior_layout`, then build them as `transit`-style interiors).

## From Grok's interior views (5)

`school_bus`, `transit_bus`, `tram`, `sightseeing_trolley`, `passenger_train`

## Hand-built with the model (4)

`city_car`, `minivan`, `personal_aerostat`, `bicycle` (remake/blender/vehicles; the bicycle has none)

## Extrapolated (67): kit/cabin.py

Glazing cut into the windows, the cabin hollowed and lined, carpet, seats in rows to the seat count, a dash with gauges and the wheel on the left, in a 1970s scheme (grey vinyl for work vehicles).

| vehicle | scheme | seats | windows |
|---|---|---|---|
| `sedan` | tan | 5 | found in the drawing |
| `station_wagon` | avocado | 5 | estimated from the shape |
| `crossover_suv` | avocado | 2 | found in the drawing |
| `full_size_suv` | avocado | 7 | found in the drawing |
| `pickup_truck` | oxblood | 2 | found in the drawing |
| `sports_car` | tan | 2 | found in the drawing |
| `convertible` | tan | 4 | estimated from the shape |
| `luxury_sedan` | charcoal | 5 | estimated from the shape |
| `taxi` | avocado | 4 | found in the drawing |
| `company_car` | vinyl | 5 | estimated from the shape |
| `unmarked_car` | vinyl | 5 | found in the drawing |
| `police_car` | vinyl | 5 | estimated from the shape |
| `police_suv` | vinyl | 5 | found in the drawing |
| `fire_chief_car` | vinyl | 5 | found in the drawing |
| `hearse` | vinyl | 2 | found in the drawing |
| `limousine` | vinyl | 2 | found in the drawing |
| `riding_mower` | charcoal | 1 | found in the drawing |
| `motorhome` | avocado | 5 | found in the drawing |
| `hotel_shuttle` | avocado | 2 | found in the drawing |
| `freight_locomotive` | vinyl | 2 | found in the drawing |
| `hi_rail_truck` | vinyl | 2 | found in the drawing |
| `delivery_van` | vinyl | 2 | found in the drawing |
| `parcel_van` | vinyl | 2 | found in the drawing |
| `mail_truck` | vinyl | 1 | found in the drawing |
| `box_truck` | vinyl | 2 | found in the drawing |
| `refrigerated_truck` | vinyl | 2 | found in the drawing |
| `semi_truck` | vinyl | 2 | found in the drawing |
| `milk_tanker` | vinyl | 2 | found in the drawing |
| `grain_truck` | vinyl | 2 | found in the drawing |
| `tow_truck` | vinyl | 2 | found in the drawing |
| `service_van` | vinyl | 2 | found in the drawing |
| `utility_bucket_truck` | vinyl | 1 | found in the drawing |
| `food_truck` | vinyl | 2 | found in the drawing |
| `row_crop_tractor` | vinyl | 1 | found in the drawing |
| `combine_harvester` | vinyl | 1 | found in the drawing |
| `crop_sprayer` | vinyl | 1 | found in the drawing |
| `skid_steer` | vinyl | 1 | found in the drawing |
| `utv` | vinyl | 2 | found in the drawing |
| `atv` | vinyl | 1 | found in the drawing |
| `farm_pickup_flatbed` | vinyl | 2 | found in the drawing |
| `dump_truck` | vinyl | 2 | found in the drawing |
| `cement_mixer` | vinyl | 2 | found in the drawing |
| `backhoe_loader` | vinyl | 1 | found in the drawing |
| `mobile_crane` | vinyl | 2 | found in the drawing |
| `low_loader` | vinyl | 2 | found in the drawing |
| `yard_tug` | vinyl | 1 | found in the drawing |
| `fire_engine` | vinyl | 6 | found in the drawing |
| `ladder_truck` | vinyl | 3 | found in the drawing |
| `ambulance` | vinyl | 4 | found in the drawing |
| `coast_guard_boat` | vinyl | 6 | found in the drawing |
| `lifeguard_truck` | vinyl | 2 | found in the drawing |
| `garbage_truck` | vinyl | 2 | found in the drawing |
| `recycling_truck` | vinyl | 2 | found in the drawing |
| `street_sweeper` | vinyl | 1 | found in the drawing |
| `public_works_pickup` | vinyl | 3 | estimated from the shape |
| `parks_mower` | vinyl | 1 | estimated from the shape |
| `lobster_boat` | oxblood | 3 | found in the drawing |
| `trawler` | navy | 5 | found in the drawing |
| `rowboat_dinghy` | tan | 2 | found in the drawing |
| `cabin_cruiser` | avocado | 2 | found in the drawing |
| `ferry` | oxblood | 20 | found in the drawing |
| `workboat_tug` | navy | 4 | found in the drawing |
| `kiddie_train` | tan | 3 | found in the drawing |
| `cargo_aerostat` | vinyl | 2 | found in the drawing |
| `tram_maintenance_car` | vinyl | 3 | found in the drawing |
| `supply_freighter` | vinyl | 6 | found in the drawing |
| `cargo_mule` | vinyl | 1 | found in the drawing |

## No interior

**Open, the seats are part of the model (29):** `motorcycle`, `scooter_moped`, `child_bicycle`, `cargo_bike`, `adult_tricycle`, `kick_scooter`, `skateboard`, `golf_cart`, `manual_wheelchair`, `power_wheelchair`, `mobility_scooter`, `baby_stroller`, `child_wagon`, `hospital_gurney`, `utility_tractor`, `forklift`, `travel_lift`, `rescue_board`, `fishing_skiff`, `canoe_kayak`, `sailboat`, `pontoon_boat`, `personal_watercraft`, `pedal_boat`, `go_kart`, `bumper_car`, `surrey_bike`, `eva_sled`, `utility_cart`

**Enclosed, no windows found or the cut failed: candidates for Grok interior views (8):** `paratransit_van`, `ice_cream_truck`, `armored_truck`, `excavator`, `brush_truck`, `rescue_aerostat`, `spoke_elevator_car`, `passenger_shuttle`
