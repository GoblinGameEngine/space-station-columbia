#!/usr/bin/env python3
"""The vehicle contract: every vehicle type the engine needs a model for -- who uses it, where it
lives, how big it is, what states and variants it needs, what the people handling it must be able
to do -- with how many the station needs, counted from the baked population and places.

    python3 tools/places/make_vehicles.py

Writes godot_project/remake/characters/npc_vehicles.json (the engine reads it) and
research/lives/06_vehicles.md. Reads npc_places.json, npc_place_index.json, npc_lives.json (RERUN
after rebaking those), npc_traits.json and research/roles/roles.json to validate every link.

As with buildings, these are TYPES and roles, not designs: the station's design language (the
existing pod, van and aerostat) decides the look in the game bible; the models come after, built
to these slots (size, seats, doors, states).
"""
import hashlib
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
CH = os.path.join(ROOT, "godot_project", "remake", "characters")

V = {}


def v(id, name, cat, medium, size, seats, who, per_place=None, occupations=(), roles=(), status="needed", priority=2,
      states=(), variants=(), actions=(), note="", household=None, per_town=0.0):
    V[id] = dict(name=name, category=cat, medium=medium, size_m=list(size), seats=seats, who=who, per_place=per_place or {}, per_town=per_town,
                 occupations=list(occupations), roles=list(roles), status=status, priority=priority, states=list(states),
                 variants=list(variants), npc_actions=list(actions), note=note, household=household)


CAR_STATES = ["parked", "charging", "moving", "doors_open", "boot_open", "headlights", "brake_lights", "indicators", "occupied"]
CAR_VARIANTS = ["colour", "condition: new / kept / worn / beater / derelict (from finances)", "age of model"]
CAR_ACTS = ["get_in_driver", "get_in_passenger", "get_out", "open_boot_load", "buckle_child"]
WORK = ["parked", "charging", "moving", "doors_open", "rear_open", "working_lights", "occupied"]

# -- 1. household: people's own (car_access, commute_mode, household, finances) ---------------------------
v("city_car", "City car / small hatchback", "household", "road", [3.6, 1.7, 1.5], 4,
  "young adults, singles, low wages, second cars", status="exists: pod (2-seat)", priority=1, states=CAR_STATES,
  variants=CAR_VARIANTS, actions=CAR_ACTS, household="car", note="The pod is the station's city car.")
v("sedan", "Sedan", "household", "road", [4.8, 1.85, 1.45], 5, "the default private car; older drivers", priority=1,
  states=CAR_STATES, variants=CAR_VARIANTS, actions=CAR_ACTS, household="car")
v("station_wagon", "Station wagon / estate", "household", "road", [4.8, 1.85, 1.5], 5, "families with dogs, gear, groceries",
  priority=3, states=CAR_STATES, variants=CAR_VARIANTS, actions=CAR_ACTS, household="car")
v("crossover_suv", "Crossover / SUV", "household", "road", [4.7, 1.9, 1.7], 5, "families; the commonest new car", priority=1,
  states=CAR_STATES, variants=CAR_VARIANTS, actions=CAR_ACTS, household="car")
v("full_size_suv", "Full-size SUV", "household", "road", [5.3, 2.0, 1.9], 7, "large families, the comfortable, towing", priority=2,
  states=CAR_STATES, variants=CAR_VARIANTS, actions=CAR_ACTS, household="car")
v("minivan", "Minivan / people carrier", "household", "road", [5.1, 2.0, 1.8], 7, "families with young children; carpools",
  status="exists: van", priority=1, states=CAR_STATES + ["sliding_door_open"], variants=CAR_VARIANTS, actions=CAR_ACTS, household="car")
v("pickup_truck", "Pickup truck", "household", "road", [5.8, 2.0, 1.9], 5, "farmers, builders, fishers, mechanics, rural households",
  priority=1, states=CAR_STATES + ["tailgate_open", "bed_loaded"], variants=CAR_VARIANTS + ["bed load: tools / feed / lumber / nets"],
  actions=CAR_ACTS + ["load_bed"], household="car")
v("sports_car", "Sports car / coupe", "household", "road", [4.5, 1.85, 1.3], 2, "the wealthy, the young who spend", priority=3,
  states=CAR_STATES, variants=CAR_VARIANTS, actions=CAR_ACTS, household="car")
v("convertible", "Convertible", "household", "road", [4.6, 1.85, 1.35], 4, "resort towns, retirees, show-offs", priority=3,
  states=CAR_STATES + ["roof_down"], variants=CAR_VARIANTS, actions=CAR_ACTS, household="car")
v("luxury_sedan", "Luxury sedan", "household", "road", [5.1, 1.9, 1.5], 5, "the wealthy: doctors, lawyers, bankers", priority=2,
  states=CAR_STATES, variants=CAR_VARIANTS, actions=CAR_ACTS, household="car")
v("motorcycle", "Motorcycle", "household", "road", [2.2, 0.8, 1.2], 2, "some adults, mostly men 18-60; a second vehicle", priority=2,
  states=["parked_on_stand", "moving", "headlight"], variants=["cruiser / sport / touring", "colour", "condition"],
  actions=["mount", "dismount", "put_on_helmet", "ride"], household="motorcycle")
v("scooter_moped", "Scooter / moped", "household", "road", [1.8, 0.7, 1.15], 2, "16-17s, students, adults without a car", priority=2,
  states=["parked_on_stand", "moving"], variants=["colour"], actions=["mount", "dismount", "ride"], household="moped")
v("bicycle", "Bicycle (adult)", "household", "road_or_path", [1.8, 0.6, 1.1], 1, "commute_mode bike; leisure riders; bike rentals",
  priority=1, states=["parked_in_rack", "leaning", "moving"], variants=["city / road / mountain / beach cruiser", "basket", "colour", "rental livery"],
  actions=["mount", "dismount", "pedal", "push_walking", "lock_to_rack"], household="bicycle",
  note="NPC cyclists ride it (NpcBike); parked ones by their owners' doors are the player's to ride.")
v("child_bicycle", "Child's bicycle", "household", "path", [1.3, 0.5, 0.8], 1, "children 4-12", priority=2,
  states=["lying_on_lawn", "moving"], variants=["training wheels", "colour"], actions=["pedal", "fall_off"], household="child_bike")
v("cargo_bike", "Cargo bike / e-bike", "household", "road_or_path", [2.4, 0.7, 1.1], 3, "carless parents, shop deliveries", priority=3,
  states=["parked", "moving", "box_loaded"], variants=["box / longtail", "child seat"], actions=["mount", "pedal", "load"], household="cargo_bike")
v("adult_tricycle", "Adult tricycle", "household", "road_or_path", [1.9, 0.8, 1.1], 1, "elders who can no longer balance", priority=3,
  states=["parked", "moving"], variants=["basket"], actions=["pedal"], household="trike")
v("kick_scooter", "Kick scooter", "household", "path", [0.9, 0.4, 1.0], 1, "children and teens", priority=3,
  states=["lying", "moving"], variants=["colour"], actions=["kick_ride"], household="kids_toys")
v("skateboard", "Skateboard", "household", "path", [0.8, 0.2, 0.1], 1, "teens", priority=3,
  states=["carried", "moving"], variants=["deck art"], actions=["push_ride", "carry"], household="kids_toys")
v("golf_cart", "Golf cart / neighbourhood vehicle", "household", "road_or_path", [2.4, 1.2, 1.8], 2, "retirees and resort households",
  priority=3, states=["parked", "moving"], variants=["canopy colour", "rental livery"], actions=["get_in", "drive"], household="golf_cart")
v("riding_mower", "Riding mower / lawn tractor", "household", "lawn", [1.8, 1.1, 1.1], 1, "houses with lawns; groundskeepers",
  priority=3, states=["in_shed", "mowing"], variants=["colour"], actions=["ride_mow"], household="mower")
v("motorhome", "Motorhome / RV", "household", "road", [9.0, 2.5, 3.5], 6, "retirees; lake-resort visitors", priority=3,
  states=["parked", "moving", "awning_out", "door_open"], variants=["class A / C"], actions=["get_in", "sit_under_awning"], household="rv")
v("camper_trailer", "Travel trailer / camper", "household", "road", [7.0, 2.4, 3.0], 0, "families who camp; parked beside houses",
  priority=3, states=["parked", "hitched"], variants=["size", "condition"], household="camper")
v("utility_trailer", "Utility trailer", "household", "road", [3.5, 1.8, 1.0], 0, "rural households, builders, farmers",
  priority=3, states=["parked", "hitched", "loaded"], variants=["load"], household="trailer")
v("boat_trailer", "Boat on trailer", "household", "road", [6.5, 2.4, 2.2], 0, "boat owners: in driveways and at the ramp",
  priority=3, states=["parked", "hitched", "at_ramp"], variants=["boat type"], household="boat")

# -- 2. personal mobility aids (traits: mobility_aid; age < 3) ------------------------------------------
v("manual_wheelchair", "Manual wheelchair", "mobility", "path", [1.1, 0.65, 0.9], 1, "mobility_aid wheelchair", priority=1,
  states=["occupied_moving", "occupied_still", "folded"], variants=["standard / sport"], actions=["wheel_self", "be_pushed", "push_wheelchair", "transfer"],
  household="wheelchair", note="16 residents now; they currently walk with the slow gait.")
v("power_wheelchair", "Power wheelchair", "mobility", "path", [1.1, 0.7, 1.0], 1, "wheelchair users with less arm strength; elders",
  priority=2, states=["occupied_moving", "occupied_still"], actions=["joystick_drive", "transfer"], household="power_chair")
v("mobility_scooter", "Mobility scooter", "mobility", "path", [1.4, 0.65, 1.1], 1, "elders with walkers or canes who go shopping",
  priority=2, states=["parked", "moving", "basket_loaded"], actions=["mount", "drive"], household="mobility_scooter")
v("rollator", "Rollator / walker", "mobility", "path", [0.7, 0.6, 0.9], 0, "mobility_aid walker", priority=1,
  states=["pushed", "sat_on"], actions=["walk_with_rollator", "sit_on_rollator"], household="rollator",
  note="The cane is a hand prop (NpcProps), not a vehicle.")
v("baby_stroller", "Baby stroller / pram", "mobility", "path", [1.0, 0.6, 1.05], 1, "households with a child under 3", priority=1,
  states=["pushed", "parked", "hood_up", "occupied"], variants=["pram / umbrella / jogging / double"], actions=["push_stroller", "lift_child_out"],
  household="stroller")
v("child_wagon", "Child's pull wagon", "mobility", "path", [1.0, 0.5, 0.5], 1, "families at the beach, park and fair", priority=3,
  states=["pulled", "loaded"], actions=["pull_wagon"], household="kids_toys")

# -- 3. hand-propelled carts at places ------------------------------------------------------------------
v("shopping_cart", "Shopping cart", "cart", "indoor_or_lot", [1.0, 0.6, 1.0], 0, "grocery and big-box shoppers",
  per_place={"grocery": 12, "hardware": 4}, priority=1, states=["corralled", "pushed", "loaded", "abandoned"], actions=["push_cart", "load_cart"])
v("hand_truck", "Hand truck / dolly", "cart", "indoor_or_lot", [0.5, 0.5, 1.3], 0, "stockers, delivery drivers, movers",
  per_place={"grocery": 1, "variety_store": 1, "liquor_store": 1, "warehouse": 2, "furniture": 1, "hardware": 1}, occupations=["driver", "shop_clerk"], priority=2,
  states=["standing", "pushed_loaded"], actions=["tilt_and_push"])
v("pallet_jack", "Pallet jack", "cart", "indoor", [1.6, 0.7, 1.2], 0, "warehouse, cannery, factory, grocery back rooms",
  per_place={"warehouse": 2, "cannery": 2, "factory": 2, "grocery": 1, "machine_works": 1}, priority=2, states=["parked", "pulled_loaded"], actions=["pump_and_pull"])
v("luggage_cart", "Luggage cart", "cart", "indoor", [1.4, 0.7, 1.9], 0, "hotel staff and guests", per_place={"hotel": 2}, occupations=["hotel_worker"],
  priority=3, states=["empty", "loaded"], actions=["push_cart"])
v("housekeeping_cart", "Housekeeping cart", "cart", "indoor", [1.3, 0.55, 1.2], 0, "hotel and motel housekeepers, janitors",
  per_place={"hotel": 2, "motel": 1, "hospital": 4, "school": 1}, occupations=["hotel_worker", "janitor"], priority=3, states=["parked", "pushed"], actions=["push_cart"])
v("hospital_gurney", "Gurney / stretcher", "cart", "indoor", [2.0, 0.7, 0.9], 1, "hospital, ambulance crews, funeral home",
  per_place={"hospital": 6, "funeral_home": 1}, occupations=["nurse", "doctor"], roles=["emt"], priority=2, states=["empty", "occupied", "pushed"], actions=["push_gurney", "lie_on_gurney"])
v("food_cart", "Street food cart", "cart", "path", [1.8, 0.9, 2.1], 0, "vendors at beaches, parks and fairs (a mobile food stand)",
  per_place={"park_pavilion": 0.5}, occupations=["shop_clerk"], priority=3, states=["parked_serving", "pushed", "umbrella_up"], actions=["serve_from_cart", "push_cart"])
v("wheelbarrow", "Wheelbarrow", "cart", "path", [1.5, 0.7, 0.7], 0, "builders, farmhands, gardeners", per_place={"construction_yard": 4, "farm": 1},
  occupations=["builder", "farmhand"], priority=3, states=["standing", "pushed_loaded"], actions=["push_wheelbarrow", "tip"])

# -- 4. public transport ----------------------------------------------------------------------------------
v("school_bus", "School bus", "transit", "road", [12.0, 2.5, 3.2], 60, "commute_mode school_bus (students)",
  per_place={"school": 1}, occupations=["driver"], roles=["truck_driver"], priority=1,
  states=["parked", "moving", "stop_arm_out", "doors_open", "flashing_lights"], variants=["full / short bus"], actions=["board_bus", "alight_bus", "drive_bus"])
v("transit_bus", "Transit bus", "transit", "road", [12.0, 2.55, 3.1], 70, "commute_mode transit between towns; carless errands",
  per_place={}, occupations=["driver"], priority=1, states=["moving", "at_stop", "doors_open", "kneeling", "destination_sign"],
  actions=["wait_at_stop", "board_bus", "alight_bus", "drive_bus"], household="transit_riders",
  note="NpcLife calls transit 'the tram'. The game bible chooses bus, tram or both; stops are a street-furniture contract.")
v("tram", "Road tram (articulated, rubber-tyred)", "transit", "road", [24.0, 2.65, 3.5], 150, "transit riders; station transit_station", per_place={"transit_station": 2},
  occupations=["driver"], priority=1, states=["moving", "at_stop", "doors_open", "kneeling", "charging_at_stop", "destination_sign"], actions=["board", "alight", "stand_holding_strap"],
  note="Canon: trams run on roads (a guided, articulated electric vehicle in its own lane, charging at stops). The station's transit (transit_station).")
v("paratransit_van", "Paratransit / patient transport van", "transit", "road", [6.0, 2.0, 2.6], 8, "wheelchair users, elders, clinic trips",
  per_place={"hospital": 2, "care_home": 1}, occupations=["driver", "care_aide"], priority=2, states=WORK + ["wheelchair_lift_down"], actions=["ride_lift", "strap_wheelchair"])
v("hotel_shuttle", "Hotel / resort shuttle", "transit", "road", [6.5, 2.0, 2.6], 12, "hotel guests, the ferry, the college",
  per_place={"hotel": 0.3, "college": 1}, occupations=["driver", "hotel_worker"], priority=3, states=WORK, variants=["livery"], actions=["board", "alight"])
v("taxi", "Taxi / ride-hail car", "transit", "road", [4.9, 1.85, 1.5], 4, "people without cars at night; the ferry and the port",
  per_place={}, occupations=["driver"], priority=2, states=CAR_STATES + ["roof_sign_lit"], household="taxi", note="A sedan or van with a roof sign and livery.")
v("sightseeing_trolley", "Sightseeing trolley (road)", "transit", "road", [9.0, 2.5, 3.2], 30, "resort-town visitors", per_place={"community_hall": 0},
  occupations=["driver"], priority=3, states=["moving", "at_stop"], note="Lake-resort towns (npc_settlements lake_resort).", household="resort_trolley")

# -- 5. rail (the station has a rail line with 146 level crossings) -------------------------------------
v("passenger_train", "Passenger train (locomotive + coaches, or a multiple unit)", "rail", "rail", [80.0, 3.0, 4.2], 300,
  "long trips between towns; the depot", per_place={"warehouse": 0}, occupations=["driver"], priority=1,
  states=["moving", "at_platform", "doors_open", "horn", "headlights"], actions=["board_train", "alight_train", "wait_on_platform"],
  household="rail", note="There is one rail line on the map; its level crossings already exist.")
v("freight_locomotive", "Electric freight locomotive", "rail", "rail", [22.0, 3.1, 4.6], 2, "freight to the grain elevator, mills, works, cannery",
  occupations=["driver"], priority=2, states=["moving", "standing", "horn", "headlights"], household="rail")
v("boxcar", "Boxcar", "rail", "rail", [15.5, 3.2, 4.6], 0, "general freight: works, mills, warehouse", priority=2,
  states=["coupled", "on_siding", "door_open"], variants=["livery", "weathering"], household="rail")
v("covered_hopper", "Covered hopper (grain)", "rail", "rail", [18.0, 3.2, 4.4], 0, "the grain elevator and the flour mill", priority=2,
  per_place={"grain_elevator": 3, "mill": 2}, states=["coupled", "on_siding", "loading"], household="rail")
v("tank_car", "Tank car", "rail", "rail", [18.0, 3.2, 4.6], 0, "liquids for the works: water, oils, process chemicals, milk in bulk", priority=3,
  states=["coupled", "on_siding"], household="rail")
v("flatcar", "Flatcar (lumber, machinery)", "rail", "rail", [18.0, 3.0, 1.3], 0, "builders' yards, machine works", priority=3,
  states=["coupled", "on_siding", "loaded"], variants=["load"], household="rail")
v("reefer_car", "Refrigerated car", "rail", "rail", [18.0, 3.2, 4.6], 0, "the cannery, the ice plant, the fish houses", priority=3,
  per_place={"cannery": 2}, states=["coupled", "on_siding", "door_open"], household="rail")
v("hi_rail_truck", "Track maintenance (hi-rail) truck", "rail", "rail_or_road", [6.5, 2.1, 2.3], 3, "track crews", occupations=["builder", "mechanic"],
  priority=3, states=WORK + ["rail_wheels_down"], household="rail")

# -- 6. commercial and trade -----------------------------------------------------------------------------
v("delivery_van", "Delivery van (shops)", "commercial", "road", [5.9, 2.0, 2.6], 2, "florist, bakery, pharmacy, laundry, variety deliveries",
  per_place={"grocery": 0.5, "bakery": 0.5, "florist": 1, "drug_store": 0.5, "laundromat": 0.3, "print_shop": 0.5, "repair_shop": 0.5},
  occupations=["driver", "shop_clerk"], status="exists: van (can take a shop livery)", priority=1, states=WORK, variants=["business livery (procedural sign text)"],
  actions=["carry_parcel", "open_rear_doors"])
v("parcel_van", "Parcel delivery van", "commercial", "road", [6.5, 2.1, 2.9], 2, "home deliveries (the parcel carrier)",
  per_place={"post_office": 0.5, "warehouse": 1}, occupations=["driver", "postal_worker"], priority=2, states=WORK, variants=["carrier livery"],
  actions=["carry_parcel", "leave_on_porch"])
v("mail_truck", "Mail truck", "commercial", "road", [4.5, 1.9, 2.4], 1, "postal workers' rounds", per_place={"post_office": 2},
  occupations=["postal_worker"], roles=["postal_worker"], priority=1, states=WORK, actions=["put_mail_in_box", "carry_satchel"],
  note="Right-hand drive so the carrier reaches kerbside mailboxes.")
v("box_truck", "Box truck", "commercial", "road", [8.0, 2.4, 3.4], 3, "furniture, appliances, groceries in bulk, movers",
  per_place={"furniture": 1, "warehouse": 1, "grocery": 0.2, "construction_yard": 0.5}, occupations=["driver"], roles=["truck_driver"], priority=2,
  states=WORK + ["lift_gate_down"], variants=["livery", "moving-company"], actions=["unload_box_truck"])
v("refrigerated_truck", "Refrigerated truck", "commercial", "road", [8.5, 2.5, 3.6], 2, "fish, ice, the cannery, groceries",
  per_place={"cannery": 1, "fish_house": 0.5, "ice_plant": 1, "fish_market": 0.5}, occupations=["driver"], priority=3, states=WORK + ["reefer_running"])
v("semi_truck", "Semi tractor-unit", "commercial", "road", [7.0, 2.5, 4.0], 2, "freight in and out of the works, mill, warehouse, cannery",
  per_place={"factory": 1, "machine_works": 0.5, "mill": 0.5, "warehouse": 1, "cannery": 1}, occupations=["driver"], roles=["truck_driver"], priority=2,
  states=["parked", "moving", "hitched", "charging"], variants=["day cab / sleeper", "colour"], actions=["climb_into_cab", "hitch_trailer"])
v("semi_trailer_dry", "Semi trailer (dry van)", "commercial", "road", [16.2, 2.6, 4.1], 0, "at loading docks", per_place={"factory": 2, "warehouse": 3, "machine_works": 1},
  priority=2, states=["at_dock", "hitched", "doors_open"], variants=["livery"])
v("semi_trailer_reefer", "Semi trailer (refrigerated)", "commercial", "road", [16.2, 2.6, 4.1], 0, "cannery, ice plant, fish houses",
  per_place={"cannery": 2, "ice_plant": 0.5}, priority=3, states=["at_dock", "hitched", "reefer_running"])
v("milk_tanker", "Milk tanker truck", "commercial", "road", [11.0, 2.5, 3.5], 2, "collecting from dairy farms", per_place={"farm": 0.05},
  occupations=["driver"], priority=3, states=WORK + ["hose_connected"])
v("grain_truck", "Grain truck", "commercial", "road_or_field", [9.0, 2.5, 3.3], 2, "harvest: fields to the elevator",
  per_place={"farm": 0.25, "grain_elevator": 1}, occupations=["farmer", "farmhand", "driver"], priority=2, states=WORK + ["tipping", "tarp_open"])
v("tow_truck", "Tow truck", "commercial", "road", [7.0, 2.4, 2.8], 2, "the garage: breakdowns and crashes", per_place={"auto_repair": 1},
  occupations=["mechanic"], priority=2, states=WORK + ["towing", "beacon_on"], actions=["hook_car"])
v("service_van", "Trades van (plumber, electrician, repair)", "commercial", "road", [5.9, 2.0, 2.6], 2, "builders, mechanics, repairers on call",
  per_place={"construction_yard": 1, "repair_shop": 0.5}, occupations=["builder", "mechanic"], roles=["plumber", "electrician", "carpenter"],
  status="exists: van (with ladder rack and livery)", priority=2, states=WORK + ["ladder_rack_loaded"], variants=["trade livery"], actions=["unload_tools"])
v("utility_bucket_truck", "Utility bucket truck", "commercial", "road", [9.0, 2.5, 3.5], 2, "power and phone lines; the station's power techs",
  per_place={"power_station": 2, "town_hall": 0.3}, occupations=["mechanic"], roles=["power_tech", "electrician"], priority=3, states=WORK + ["bucket_raised", "outriggers_down"])
v("food_truck", "Food truck", "commercial", "road", [7.0, 2.4, 3.2], 2, "lunch trade at works and beaches; festivals",
  per_place={"food_stand": 0.3, "diner": 0.1}, occupations=["cook"], priority=3, states=["parked_serving", "moving", "hatch_open"], variants=["cuisine livery"], actions=["serve_from_hatch"])
v("ice_cream_truck", "Ice-cream van", "commercial", "road", [6.0, 2.0, 2.8], 2, "summer streets in resort towns", per_place={"food_stand": 0.2},
  occupations=["shop_clerk"], priority=3, states=["moving_chiming", "parked_serving"], actions=["queue_at_hatch"])
v("armored_truck", "Armoured cash truck", "commercial", "road", [6.5, 2.3, 2.8], 3, "banks' cash runs", per_place={"bank": 0.2},
  occupations=["driver"], roles=["security_guard"], priority=3, states=WORK, actions=["carry_cash_bag"])
v("hearse", "Hearse", "commercial", "road", [5.8, 2.0, 1.7], 2, "the funeral home", per_place={"funeral_home": 1}, priority=3,
  states=CAR_STATES + ["rear_open"], actions=["carry_coffin"])
v("limousine", "Limousine / wedding car", "commercial", "road", [7.5, 2.0, 1.5], 8, "hotels, weddings, proms", per_place={"hotel": 0.1, "funeral_home": 0.5},
  occupations=["driver"], priority=3, states=CAR_STATES)
v("company_car", "Company car / realtor's car", "commercial", "road", [4.8, 1.85, 1.5], 5, "agents, lawyers, managers on the road",
  per_place={"insurance_office": 0.3, "law_office": 0.2, "bank": 0.2}, occupations=["agent"], priority=3, states=CAR_STATES, variants=["magnetic door sign"],
  note="A sedan or crossover with a business sign.")

# -- 7. farm (136 farms; machinery listed in npc_places) -----------------------------------------------
v("utility_tractor", "Utility tractor", "farm", "field_or_road", [4.0, 2.0, 2.8], 1, "every farm's workhorse", per_place={"farm": 1},
  occupations=["farmer", "farmhand"], roles=["farmer"], priority=1, states=["parked", "working", "moving_on_road", "slow_vehicle_sign", "implement_attached", "front_loader_raised"],
  variants=["colour (brand-like)", "age"], actions=["climb_into_tractor", "drive_tractor"])
v("row_crop_tractor", "Large row-crop tractor", "farm", "field_or_road", [6.0, 3.0, 3.6], 1, "big crop farms", per_place={"farm": 0.35},
  occupations=["farmer", "farmhand"], priority=2, states=["parked", "working", "implement_attached"], variants=["duals"])
v("combine_harvester", "Combine harvester", "farm", "field_or_road", [9.0, 3.5, 4.0], 1, "grain harvest", per_place={"farm": 0.15},
  occupations=["farmer"], priority=2, states=["parked", "harvesting", "unloading_auger_out", "header_detached"], actions=["climb_ladder"])
v("grain_cart", "Grain cart", "farm", "field", [7.0, 3.5, 3.8], 0, "harvest, alongside the combine", per_place={"farm": 0.15}, priority=3, states=["hitched", "unloading"])
v("hay_baler", "Baler", "farm", "field", [5.0, 2.8, 2.4], 0, "hay and straw", per_place={"farm": 0.3}, priority=3, states=["hitched", "working", "bale_ejecting"])
v("hay_wagon", "Hay wagon / flatbed farm wagon", "farm", "field_or_road", [6.0, 2.4, 1.2], 0, "hauling bales; hayrides at the fair",
  per_place={"farm": 0.6}, priority=3, states=["hitched", "loaded", "hayride"], actions=["stack_bales", "sit_on_hay"])
v("planter_drill", "Planter / seed drill", "farm", "field", [6.0, 9.0, 2.0], 0, "spring planting", per_place={"farm": 0.3}, priority=3, states=["folded", "working"])
v("crop_sprayer", "Crop sprayer", "farm", "field", [8.0, 3.0, 3.5], 1, "crop care", per_place={"farm": 0.1}, priority=3, states=["booms_folded", "spraying"])
v("manure_spreader", "Manure spreader", "farm", "field", [6.0, 2.5, 2.5], 0, "livestock farms", per_place={"farm": 0.25}, priority=3, states=["hitched", "spreading"])
v("plough_disc", "Plough / disc harrow", "farm", "field", [4.0, 4.0, 1.5], 0, "tillage", per_place={"farm": 0.5}, priority=3, states=["hitched", "working"])
v("skid_steer", "Skid-steer loader", "farm", "yard", [3.0, 1.8, 2.0], 1, "barns, builders' yards", per_place={"farm": 0.3, "construction_yard": 1},
  occupations=["farmhand", "builder"], priority=3, states=["parked", "working", "bucket_raised"])
v("utv", "UTV / side-by-side", "farm", "field_or_path", [3.0, 1.6, 1.9], 2, "farms, lifeguards, groundskeepers, parks",
  per_place={"farm": 0.5, "lighthouse": 0.5}, occupations=["farmhand", "farmer"], priority=2, states=["parked", "moving", "bed_loaded"], variants=["farm / lifeguard livery"])
v("atv", "ATV / quad", "farm", "field_or_path", [2.1, 1.2, 1.2], 1, "farm checks, beach patrol, rural teens", per_place={"farm": 0.4},
  occupations=["farmhand"], priority=3, states=["parked", "moving"], household="atv")
v("livestock_trailer", "Livestock trailer", "farm", "road", [7.0, 2.4, 2.4], 0, "livestock farms, the fair", per_place={"farm": 0.3}, priority=3, states=["parked", "hitched", "ramp_down"])
v("farm_pickup_flatbed", "Farm flatbed truck", "farm", "road_or_field", [6.5, 2.4, 2.2], 3, "feed, fencing, bales", per_place={"farm": 0.3},
  occupations=["farmer", "farmhand"], priority=3, states=WORK + ["bed_loaded"])

# -- 8. construction and industry -------------------------------------------------------------------------
v("forklift", "Forklift", "industry", "indoor_or_yard", [3.3, 1.2, 2.2], 1, "warehouse, works, mill, cannery, builders' and garden yards",
  per_place={"warehouse": 2, "factory": 3, "machine_works": 2, "mill": 1, "cannery": 2, "grain_elevator": 1, "construction_yard": 1, "hardware": 0.3, "fish_house": 0.3},
  occupations=["factory_hand", "dock_worker"], priority=1, states=["parked", "moving", "forks_raised", "loaded_pallet", "reversing_beeper"], actions=["drive_forklift"])
v("dump_truck", "Dump truck", "industry", "road", [8.0, 2.5, 3.2], 2, "builders, the town's public works", per_place={"construction_yard": 1, "town_hall": 0.5},
  occupations=["builder", "driver"], priority=2, states=WORK + ["tipping"], per_town=0.3)
v("cement_mixer", "Concrete mixer truck", "industry", "road", [9.5, 2.5, 3.8], 2, "building sites", per_place={"construction_yard": 1},
  occupations=["builder", "driver"], priority=3, states=WORK + ["drum_turning", "chute_out"])
v("backhoe_loader", "Backhoe loader", "industry", "road_or_site", [7.0, 2.4, 3.8], 1, "digging: sites, pipes, graves", per_place={"construction_yard": 1, "town_hall": 0.3},
  occupations=["builder"], priority=2, states=["parked", "digging", "loader_raised", "stabilisers_down"], per_town=0.2)
v("excavator", "Excavator", "industry", "site", [9.5, 2.9, 3.0], 1, "bigger sites, the harbour, the station works", per_place={"construction_yard": 0.5},
  occupations=["builder"], priority=3, states=["parked", "digging", "on_low_loader"])
v("mobile_crane", "Mobile crane", "industry", "road_or_site", [12.0, 2.6, 3.8], 2, "building sites, the boatyard, the port", per_place={"construction_yard": 0.2, "port": 1},
  occupations=["builder", "dock_worker"], priority=3, states=["travelling", "outriggers_down", "boom_raised", "lifting"])
v("low_loader", "Low-loader (machinery transport)", "industry", "road", [18.0, 2.6, 3.5], 2, "moving diggers, tractors, boats", per_place={"construction_yard": 0.2},
  occupations=["driver"], priority=3, states=WORK + ["loaded"])
v("travel_lift", "Boat travel lift", "industry", "yard", [10.0, 7.0, 9.0], 1, "the boatyard (lifts boats out of the water)",
  per_place={"boatyard": 1}, occupations=["builder", "mechanic"], priority=2, states=["empty", "lifting_boat", "moving"])
v("yard_tug", "Yard tractor / port tug", "industry", "yard", [5.5, 2.6, 3.5], 1, "moving trailers at docks and the port",
  per_place={"port": 3, "warehouse": 0.3}, occupations=["dock_worker"], roles=["cargo_handler"], priority=3, states=["moving", "hitched"])

# -- 9. emergency and civic -------------------------------------------------------------------------------
v("police_car", "Police patrol car", "emergency", "road", [5.1, 1.95, 1.5], 5, "police patrols", per_place={"police_fire": 3, "courthouse": 0.5, "town_hall": 0.5},
  occupations=["police"], roles=["police", "marshal"], priority=1, states=CAR_STATES + ["light_bar_on", "siren"], variants=["town / county livery"],
  actions=["patrol_lean_on_car", "put_in_back_seat"], per_town=1)
v("police_suv", "Police SUV", "emergency", "road", [5.1, 2.0, 1.8], 5, "rural patrol, the chief", per_place={"police_fire": 1}, occupations=["police"],
  priority=2, states=CAR_STATES + ["light_bar_on", "siren"])
v("unmarked_car", "Unmarked police car", "emergency", "road", [5.0, 1.9, 1.5], 5, "detectives, the marshal", per_place={"police_fire": 0.5},
  occupations=["police"], roles=["marshal"], priority=3, states=CAR_STATES + ["dash_light_on"])
v("fire_engine", "Fire engine (pumper)", "emergency", "road", [10.0, 2.55, 3.3], 6, "firefighters", per_place={"police_fire": 1},
  occupations=["firefighter"], roles=["firefighter", "volunteer_firefighter"], priority=1, states=WORK + ["lights_siren", "hoses_out", "in_bay"],
  actions=["jump_on_engine", "pull_hose", "open_locker"], per_town=1)
v("ladder_truck", "Aerial ladder truck", "emergency", "road", [12.0, 2.55, 3.5], 4, "tall buildings: hotels, the courthouse", per_place={"police_fire": 0.5},
  occupations=["firefighter"], priority=2, states=WORK + ["ladder_raised", "outriggers_down"])
v("brush_truck", "Brush / rescue truck", "emergency", "road_or_field", [6.5, 2.2, 2.6], 3, "field fires, water rescue, rural calls",
  per_place={"police_fire": 1}, occupations=["firefighter"], roles=["volunteer_firefighter"], priority=3, states=WORK + ["lights_siren"], per_town=0.5)
v("fire_chief_car", "Fire chief's car", "emergency", "road", [5.0, 2.0, 1.8], 5, "the chief (a volunteer chief drives it home)", per_place={"police_fire": 1},
  occupations=["firefighter"], priority=3, states=CAR_STATES + ["light_bar_on"], per_town=0.5)
v("ambulance", "Ambulance", "emergency", "road", [7.0, 2.4, 2.9], 4, "EMS: the hospital, the fire station", per_place={"hospital": 2, "police_fire": 1},
  occupations=["nurse"], roles=["emt"], priority=1, states=WORK + ["lights_siren", "stretcher_out"], actions=["load_stretcher", "climb_into_back"], per_town=0.5)
v("coast_guard_boat", "Coast guard / harbour patrol boat", "emergency", "water", [10.0, 3.2, 3.5], 6, "harbourmaster, coast guard, lake rescue",
  per_place={"harbormaster": 1}, occupations=["dock_worker", "police"], roles=["port_master"], priority=2, states=["moored", "underway", "lights_on", "towing"])
v("lifeguard_truck", "Lifeguard truck / beach patrol", "emergency", "road_or_beach", [5.5, 2.0, 2.0], 2, "beach lifeguards (12 lifeguard towers)",
  per_place={"lighthouse": 0.5}, priority=3, states=WORK + ["lights_on", "rescue_board_racked"], note="Lifeguard towers are typed 'lighthouse' in the registry.")
v("rescue_board", "Rescue board / rescue paddleboard", "emergency", "water", [3.2, 0.7, 0.2], 1, "lifeguards", per_place={"lighthouse": 1}, priority=3,
  states=["racked", "paddled"], actions=["paddle_prone"])
v("garbage_truck", "Refuse truck", "civic", "road", [9.5, 2.5, 3.6], 3, "weekly collections (recyclers, public works)", per_place={"town_hall": 1, "recycling_center": 3},
  occupations=["driver", "janitor"], roles=["recycler"], priority=2, states=WORK + ["lifter_raised", "compacting"], actions=["wheel_bin_to_truck", "ride_step"], per_town=0.5)
v("recycling_truck", "Recycling truck", "civic", "road", [9.0, 2.5, 3.4], 2, "separate recycling round", per_place={"recycling_center": 2, "town_hall": 0.3},
  occupations=["driver"], roles=["recycler"], priority=3, states=WORK)
v("street_sweeper", "Street sweeper", "civic", "road", [6.0, 2.4, 3.0], 1, "main streets at dawn", per_place={"town_hall": 0.3}, occupations=["driver", "janitor"],
  priority=3, states=["parked", "sweeping", "brushes_down"])
v("public_works_pickup", "Public works pickup", "civic", "road", [5.8, 2.0, 1.9], 3, "the town's maintenance crew", per_place={"town_hall": 2},
  occupations=["builder", "janitor"], roles=["maintenance_worker"], priority=2, states=WORK + ["beacon_on"], variants=["town seal livery"], per_town=1)
v("parks_mower", "Park / grounds mower (zero-turn or gang)", "civic", "lawn", [2.5, 2.0, 1.3], 1, "parks, schools, churchyards, the cemetery",
  per_place={"school": 0.5, "park_pavilion": 0.3, "church": 0.1}, occupations=["janitor"], priority=3, states=["in_shed", "mowing"])

# -- 10. water (harbours, fish houses, boatyards, marina stores, a ferry terminal) --------------------------
v("lobster_boat", "Inshore fishing / lobster boat", "water", "water", [11.0, 3.8, 3.5], 3, "fishers (commercial, day boats)",
  per_place={"fish_house": 2}, occupations=["fisher"], priority=1, states=["moored", "underway", "hauling", "gulls_following"], variants=["name on transom", "colour"],
  actions=["haul_traps", "coil_rope", "step_aboard"])
v("trawler", "Trawler / dragger", "water", "water", [20.0, 6.0, 8.0], 5, "the cannery's supply", per_place={"cannery": 1.5}, occupations=["fisher"], priority=2,
  states=["moored", "underway", "nets_out", "unloading"])
v("fishing_skiff", "Skiff / small outboard boat", "water", "water", [5.0, 1.9, 1.2], 4, "part-time fishers, boat owners, bait shops",
  per_place={"sporting_goods": 0.5}, occupations=["fisher"], priority=2, states=["moored", "beached", "underway", "on_trailer"], household="boat")
v("rowboat_dinghy", "Rowboat / dinghy", "water", "water", [3.5, 1.4, 0.7], 3, "tenders at moorings, pond rentals", priority=3,
  states=["tied_up", "rowed", "upturned_on_shore"], actions=["row"], household="boat")
v("canoe_kayak", "Canoe / kayak", "water", "water", [4.8, 0.9, 0.5], 2, "leisure on rivers and the lake; rentals", per_place={"sporting_goods": 2},
  priority=3, states=["racked", "on_car_roof", "paddled"], actions=["paddle", "carry_overhead"], household="boat")
v("sailboat", "Sailboat", "water", "water", [9.0, 3.0, 12.0], 6, "the yacht club, the comfortable", per_place={"community_hall": 0.5}, priority=3,
  states=["moored", "sailing", "sails_furled"], household="boat", note="Yacht Club is a community_hall hint in the registry.")
v("pontoon_boat", "Pontoon boat", "water", "water", [7.5, 2.6, 2.5], 10, "lake families, retirees, rentals", priority=3, states=["moored", "underway"], household="boat")
v("cabin_cruiser", "Cabin cruiser / motor yacht", "water", "water", [12.0, 4.0, 4.0], 8, "the wealthy", priority=3, states=["moored", "underway"], household="boat")
v("personal_watercraft", "Personal watercraft (jet ski)", "water", "water", [3.3, 1.2, 1.1], 2, "young people at resorts", priority=3,
  states=["on_trailer", "underway"], household="boat")
v("ferry", "Passenger / car ferry", "water", "water", [45.0, 12.0, 10.0], 250, "across the lake: the Ferry Terminal", per_place={"harbormaster": 0.3},
  occupations=["dock_worker"], priority=2, states=["docked_ramp_down", "underway", "horn"], actions=["board_ferry", "lean_on_rail"])
v("workboat_tug", "Workboat / harbour tug", "water", "water", [15.0, 5.0, 6.0], 4, "the harbour, the boatyard, barges", per_place={"boatyard": 0.5, "harbormaster": 0.3},
  occupations=["dock_worker"], priority=3, states=["moored", "pushing", "towing"])
v("barge", "Barge", "water", "water", [40.0, 11.0, 3.0], 0, "gravel, grain and bulk goods on the lake", per_place={"grain_elevator": 0.3}, priority=3,
  states=["moored", "under_tow", "loaded"])
v("pedal_boat", "Pedal boat / swan boat", "amusement", "water", [2.5, 1.5, 1.2], 2, "park ponds, resort rentals", per_place={"amusement": 2},
  priority=3, states=["tied_up", "pedalled"], actions=["pedal_seated"])

# -- 11. amusement and leisure --------------------------------------------------------------------------
v("go_kart", "Go-kart", "amusement", "track", [1.8, 1.2, 0.9], 1, "go-kart tracks (ride placements)", per_place={"amusement": 3}, priority=3,
  states=["parked_in_pit", "racing"], actions=["drive_kart"])
v("bumper_car", "Bumper car", "amusement", "track", [2.0, 1.3, 1.1], 2, "the arcade and funfair", per_place={"amusement": 4, "arcade": 1}, priority=3,
  states=["parked", "driving", "bumping"])
v("kiddie_train", "Kiddie train", "amusement", "track", [8.0, 1.2, 1.4], 16, "the funfair, the park", per_place={"amusement": 0.5}, priority=3, states=["stopped", "running"])
v("surrey_bike", "Surrey (four-wheel pedal cart)", "amusement", "road_or_path", [2.5, 1.3, 1.9], 4, "boardwalk rentals at resorts", per_place={"sporting_goods": 1},
  priority=3, states=["parked", "pedalled"], actions=["pedal_seated"])

# -- 12. the station (station facility types; research/roles/03) -------------------------------------------
v("personal_aerostat", "Personal aerostat", "station", "air", [7.2, 7.2, 5.0], 4, "the station's own flying vehicle: towns, farms, the summoned aerostat",
  status="exists: aerostat", priority=1, states=["parked", "flying", "landing", "screen_on"], actions=["board_aerostat"])
v("cargo_aerostat", "Cargo / heavy-lift aerostat", "station", "air", [20.0, 12.0, 9.0], 2, "freight to farms and works; lifting modules", per_place={"port": 2},
  roles=["shuttle_pilot", "cargo_handler"], priority=3, states=["parked", "flying", "sling_load"], note="For the game bible: how much freight flies instead of rolling.")
v("rescue_aerostat", "Rescue / medical aerostat", "station", "air", [9.0, 8.0, 5.5], 4, "air ambulance, search and rescue", per_place={"hospital": 0.5},
  roles=["emt"], priority=3, states=["parked", "flying", "beacon_on"])
v("tram_maintenance_car", "Tram maintenance truck", "station", "road", [10.0, 2.6, 3.5], 3, "keeping the transit line", per_place={"transit_station": 0.5},
  occupations=["mechanic"], roles=["maintenance_worker"], priority=3, states=["parked", "working"])
v("spoke_elevator_car", "Spoke elevator car (floor to axis)", "station", "vertical", [6.0, 6.0, 3.0], 30, "reaching the axis, the port, zero-g",
  per_place={"port": 2, "arrival_center": 1}, roles=["arrival_coordinator"], priority=2, states=["at_floor", "climbing", "at_axis"], actions=["hold_rail_in_low_g"],
  note="The ceiling is 2,950 m up and the axis shaft 50 m across (StationGeo): the game bible decides how people get there.")
v("passenger_shuttle", "Passenger shuttle (Earth / orbit)", "station", "space", [30.0, 15.0, 8.0], 40, "arrivals and departures at the port",
  per_place={"port": 1}, roles=["shuttle_pilot", "arrival_coordinator", "quarantine_officer"], priority=2, states=["docked", "docking", "departing"])
v("supply_freighter", "Supply freighter", "station", "space", [60.0, 20.0, 20.0], 6, "the station's supplies", per_place={"port": 0.5},
  roles=["shuttle_pilot", "cargo_handler"], priority=3, states=["docked", "unloading", "departing"])
v("cargo_mule", "Cargo mule / tug (port, zero-g)", "station", "space_or_axis", [3.0, 2.0, 2.0], 1, "moving containers in the port", per_place={"port": 4},
  roles=["cargo_handler"], priority=3, states=["docked", "moving", "carrying"])
v("eva_sled", "EVA sled / maintenance pod", "station", "space", [3.0, 2.0, 2.5], 1, "hull inspection and repair", per_place={"eva_depot": 3},
  roles=["eva_tech", "hull_inspector"], priority=3, states=["docked", "outside", "arm_extended"])
v("utility_cart", "Electric utility cart", "station", "path", [3.0, 1.3, 1.9], 2, "technicians at the air plant, water works, power, hydroponics, recycling",
  per_place={"life_support_plant": 2, "water_works": 2, "power_station": 2, "hydroponics": 3, "recycling_center": 2, "admin_center": 1},
  roles=["air_plant_operator", "water_tech", "power_tech", "agronomist"], priority=2, states=["parked", "moving", "bed_loaded"])
v("hydroponics_harvest_cart", "Harvest cart (hydroponics)", "station", "indoor", [2.0, 0.8, 1.5], 0, "hydroponics workers", per_place={"hydroponics": 6},
  occupations=["farmhand"], priority=3, states=["parked", "pushed", "loaded"], actions=["push_cart"])


# -- counts -------------------------------------------------------------------------------------------------

def h01(*parts):
    return int.from_bytes(hashlib.blake2b("|".join(map(str, parts)).encode(), digest_size=8).digest(), "little") / 2 ** 64


def pick(weights, *key):
    tot = sum(weights.values())
    r = h01(*key) * tot
    for k, w in weights.items():
        r -= w
        if r <= 0:
            return k
    return k


FLEET = []                       # every road vehicle with a model, where it lives (-> npc_fleet.json)
# work vehicles that do rounds through their town, and when
ROUNDS = {"mail_truck": [8, 16], "parcel_van": [9, 18], "delivery_van": [8, 17], "police_car": [0, 24], "police_suv": [0, 24],
          "garbage_truck": [6, 13], "recycling_truck": [7, 13], "street_sweeper": [5, 9], "ice_cream_truck": [12, 19], "taxi": [6, 24],
          "tow_truck": [8, 18], "service_van": [8, 17], "public_works_pickup": [8, 16], "utility_bucket_truck": [8, 16]}


def place_fleet(units, V):
    """Work vehicles at their places (per_place), the towns' own (per_town, at the town hall), a taxi a town;
    the ones in ROUNDS do rounds through the town's places in their hours."""
    by_town = defaultdict(list)
    for u in units:
        by_town[u["settlement"]].append(u)
    drivable = {k for k, x in V.items() if x["medium"] in ("road", "road_or_path") and x["seats"] and x["category"] not in ("cart", "mobility", "rail", "household")
                and k not in ("tram", "transit_bus", "sightseeing_trolley", "passenger_shuttle")}

    def add(vid, kind, u):
        town = sorted(by_town[u["settlement"]], key=lambda x: h01("round", vid, x["uid"]))
        stops = [x["uid"] for x in town if x["uid"] != u["uid"]][:5] if kind in ROUNDS else []
        FLEET.append({"id": vid, "type": kind, "kind": "place", "at": u["uid"], "door": u["door"], "driver": "", "rounds": stops,
                      "hours": ROUNDS.get(kind, [])})
    for u in units:
        for k in sorted(drivable):
            c = V[k]["per_place"].get(u["type"], 0)
            nn = int(c) + (1 if h01("pv", u["uid"], k) < c - int(c) else 0)
            for j in range(nn):
                add("PV-%s-%s-%d" % (u["uid"], k, j), k, u)
    for town, us in sorted(by_town.items()):
        hall = next((u for t in ("town_hall", "police_fire", "community_hall", "post_office") for u in us if u["type"] == t), None)
        if hall is None:
            continue
        for k in sorted(drivable):
            c = V[k]["per_town"]
            nn = int(c) + (1 if h01("pt", town, k) < c - int(c) else 0)
            for j in range(nn):
                add("TV-%s-%s-%d" % (town.replace(" ", "_"), k, j), k, hall)
        add("TV-%s-taxi" % town.replace(" ", "_"), "taxi", hall)


def household_fleet(people, settle):
    """Private vehicles per household, from the baked residents (deterministic)."""
    hh = defaultdict(list)
    for pid, p in people.items():
        p["pid"] = pid
        hh[(p["home"], p["hh"])].append(p)
    n = Counter()
    for key, ms in hh.items():
        adults = [m for m in ms if m["age"] >= 16]
        head = max(adults, key=lambda m: m["age"]) if adults else ms[0]
        cars = sum(1 for m in adults if m["car"] == "own_car") or (1 if any(m["car"] == "shared_car" for m in adults) else 0)
        kids = [m for m in ms if m["age"] < 13]
        farm = "FARM-" in key[0]
        flat = "/" in key[0]
        resort = settle.get(ms[0]["settlement"], "") == "lake_resort"
        wealthy = any(m["finances"] == "wealthy" for m in adults)
        poor = all(m["finances"] in ("struggling", "in_debt") for m in adults) if adults else False
        trades = any(m["occupation"] in ("builder", "farmer", "farmhand", "fisher", "mechanic", "dock_worker") for m in adults)
        drivers = sorted([m for m in adults if m["car"] == "own_car"], key=lambda m: -m["age"]) or [head]
        for i in range(cars):
            w = {"sedan": 30, "city_car": 14, "crossover_suv": 28, "pickup_truck": 16, "minivan": 5, "station_wagon": 2, "sports_car": 1.5,
                 "luxury_sedan": 2, "full_size_suv": 5, "convertible": 0.7}
            if farm:
                w["pickup_truck"] *= 4
            if trades and i == 0:
                w["pickup_truck"] *= 3
            if kids:
                w["minivan"] *= 4
                w["crossover_suv"] *= 1.5
                w["full_size_suv"] *= 1.5
                w["sports_car"] *= 0.2
            if wealthy:
                w["luxury_sedan"] *= 5
                w["sports_car"] *= 3
                w["convertible"] *= 3
                w["full_size_suv"] *= 2
            if poor:
                for k in ("luxury_sedan", "sports_car", "convertible", "full_size_suv"):
                    w[k] *= 0.1
                w["city_car"] *= 1.8
            if head["age"] >= 70:
                w["sedan"] *= 1.6
                w["sports_car"] *= 0.3
            if head["age"] < 25 or i > 0:
                w["city_car"] *= 2.5
            if resort:
                w["convertible"] *= 2
            kind = pick(w, "car", key, i)
            n[kind] += 1
            d = drivers[min(i, len(drivers) - 1)]
            FLEET.append({"id": "HV-%s-%d-%d" % (key[0], key[1], i), "type": kind, "kind": "home", "at": key[0], "door": d["door"],
                          "driver": d["pid"], "rounds": [], "hours": []})
        r = lambda tag: h01(tag, key)
        men = [m for m in adults if m["sex"] == "male" and 18 <= m["age"] <= 60]
        if men and r("moto") < 0.10:
            n["motorcycle"] += 1
        n["scooter_moped"] += sum(1 for m in adults if (m["car"] == "none" or m["age"] < 18) and h01("moped", key, m["age"]) < 0.08)
        for m in ms:
            if m["commute"] == "bike" or (5 <= m["age"] <= 75 and m["age"] >= 13 and h01("bike", key, m["age"], m["sex"]) < 0.35):
                n["bicycle"] += 1
            elif 4 <= m["age"] <= 12 and h01("kbike", key, m["age"]) < 0.65:
                n["child_bicycle"] += 1
            if m["mobility"] == "wheelchair":
                n["power_wheelchair" if m["age"] >= 75 and h01("pchair", key) < 0.4 else "manual_wheelchair"] += 1
            if m["mobility"] == "walker":
                n["rollator"] += 1
            if m["mobility"] in ("walker", "cane") and m["age"] >= 70 and h01("mscoot", key, m["age"]) < 0.15:
                n["mobility_scooter"] += 1
            if m["mobility"] == "none" and m["age"] >= 75 and h01("trike", key, m["age"]) < 0.03:
                n["adult_tricycle"] += 1
        if any(m["age"] < 3 for m in ms):
            n["baby_stroller"] += 1
        if kids and h01("cargo", key) < (0.12 if cars == 0 else 0.02):
            n["cargo_bike"] += 1
        if any(8 <= m["age"] <= 17 for m in ms):
            n["kick_scooter"] += 1 if r("kick") < 0.5 else 0
            n["skateboard"] += 1 if r("skate") < 0.3 else 0
            n["child_wagon"] += 1 if r("wagon") < 0.15 else 0
        if not flat and "condo" not in key[0] and r("mower") < 0.25:
            n["riding_mower"] += 1
        if resort and r("golf") < 0.06 or head["occupation"] == "retired" and r("golf2") < 0.03:
            n["golf_cart"] += 1
        if head["age"] >= 55 and r("rv") < 0.06:
            n["motorhome"] += 1
        elif kids and r("camper") < 0.06:
            n["camper_trailer"] += 1
        if (farm or trades) and r("trailer") < 0.35 or r("trailer2") < 0.05:
            n["utility_trailer"] += 1
        if (farm or trades or resort) and r("atv") < 0.12:
            n["atv"] += 1
        if r("boat") < (0.14 if resort else 0.06):
            n["boat_owners"] += 1
            kind = pick({"fishing_skiff": 35, "canoe_kayak": 25, "pontoon_boat": 12 if resort else 4, "rowboat_dinghy": 10,
                         "personal_watercraft": 6, "sailboat": 6 if wealthy else 2, "cabin_cruiser": 5 if wealthy else 0.5}, "boatkind", key)
            n[kind] += 1
            if kind in ("fishing_skiff", "pontoon_boat", "personal_watercraft", "cabin_cruiser"):
                n["boat_trailer"] += 1
    riders = sum(1 for p in people.values() if p["commute"] == "transit")
    no_car = sum(1 for p in people.values() if p["car"] == "none" and p["age"] >= 16)
    n["transit_bus"] += max(2, round(riders / 30))
    n["taxi"] += max(1, round(no_car / 60))
    return n, len(hh)


# -- physics: mass, motor and drag for every type (research/physics/vehicle_dynamics.md) -----------------
# Every vehicle is electric or pedal-powered (canon). A motor gives its peak torque up to its base
# speed and its peak power above (EV: constant torque, then constant power); a single reduction gear
# to the wheels. Anchors are approximate published specs of real electric vehicles of the kind
# ("as"), the rest scale by category from the vehicle's size: mass from its envelope (kg per m^3 of
# L x W x H), power from a power-to-weight ratio, top speed from the kind of vehicle.
PHYS_CAT = {   # kg/m^3 of envelope, W/kg, top km/h, drive, drag coefficient
    "household": (125, 95, 170, "RWD", 0.32), "commercial": (100, 60, 120, "RWD", 0.45), "transit": (130, 25, 90, "RWD", 0.6),
    "rail": (180, 15, 120, "AWD", 0.7), "farm": (200, 25, 40, "AWD", 0.9), "industry": (190, 25, 60, "AWD", 0.8),
    "emergency": (120, 90, 160, "AWD", 0.45), "civic": (120, 30, 90, "RWD", 0.7), "station": (60, 40, 60, "AWD", 0.6),
    "amusement": (90, 20, 30, "RWD", 0.6), "mobility": (110, 8, 12, "RWD", 0.8), "cart": (60, 0, 6, "none", 0.9), "water": (60, 30, 40, "none", 0.5)}
PHYS_AS = {    # id: (mass kg, power kW, torque Nm, top km/h, drive, CdA m^2, "like")
    "city_car": (1250, 80, 250, 130, "FWD", 0.62, "a small electric hatchback"),
    "sedan": (1650, 150, 360, 175, "RWD", 0.55, "a mid-size electric sedan"),
    "station_wagon": (1800, 160, 380, 170, "FWD", 0.62, "an electric estate"),
    "crossover_suv": (1950, 200, 450, 180, "AWD", 0.75, "an electric crossover"),
    "full_size_suv": (2700, 320, 800, 180, "AWD", 1.0, "a large electric SUV"),
    "minivan": (2150, 150, 400, 160, "FWD", 0.85, "an electric people carrier"),
    "pickup_truck": (2900, 340, 1000, 170, "AWD", 1.15, "a full-size electric pickup"),
    "sports_car": (1600, 380, 650, 250, "RWD", 0.5, "an electric sports coupe"),
    "convertible": (1750, 220, 450, 220, "RWD", 0.65, "an electric roadster"),
    "luxury_sedan": (2300, 300, 650, 220, "AWD", 0.55, "a large electric luxury sedan"),
    "motorcycle": (250, 78, 116, 180, "RWD", 0.45, "a full-size electric motorcycle"),
    "scooter_moped": (100, 3, 150, 45, "RWD", 0.4, "an electric moped"),
    "bicycle": (15, 0.2, 60, 35, "RWD", 0.5, "a city bicycle; the rider's sustained 200 W"),
    "child_bicycle": (9, 0.08, 25, 20, "RWD", 0.35, "a child's bicycle and rider"),
    "golf_cart": (450, 4, 120, 25, "RWD", 1.0, "an electric golf cart"),
    "atv": (350, 30, 120, 90, "AWD", 0.8, "an electric quad"),
    "utv": (800, 50, 300, 80, "AWD", 1.2, "an electric side-by-side"),
    "delivery_van": (2900, 198, 430, 130, "RWD", 1.8, "a large electric panel van"),
    "parcel_van": (4500, 200, 600, 110, "RWD", 2.4, "an electric step van"),
    "box_truck": (8000, 220, 1200, 105, "RWD", 4.5, "a medium electric box truck"),
    "semi_truck": (10000, 400, 2500, 105, "RWD", 5.5, "an electric semi tractor"),
    "garbage_truck": (20000, 300, 3000, 90, "RWD", 6.0, "an electric refuse truck"),
    "transit_bus": (13000, 300, 2500, 100, "RWD", 6.0, "a 12 m battery-electric bus"),
    "school_bus": (12000, 240, 2000, 100, "RWD", 6.0, "an electric school bus"),
    "tram": (40000, 360, 6000, 70, "AWD", 7.0, "a 24 m articulated tram (4 x 90 kW)"),
    "passenger_train": (45000, 600, 10000, 120, "AWD", 9.0, "an electric multiple-unit car"),
    "freight_locomotive": (120000, 4000, 60000, 120, "AWD", 10.0, "an electric freight locomotive"),
    "fire_engine": (18000, 350, 3000, 120, "RWD", 6.5, "an electric fire engine"),
    "ambulance": (4500, 200, 500, 140, "RWD", 2.6, "an electric ambulance"),
    "police_car": (2000, 250, 450, 200, "AWD", 0.6, "an electric police sedan"),
    "police_suv": (2400, 300, 600, 190, "AWD", 0.85, "an electric police SUV"),
    "row_crop_tractor": (7000, 150, 4000, 40, "AWD", 3.0, "a 200 hp electric farm tractor"),
    "utility_tractor": (2500, 50, 1200, 35, "AWD", 2.0, "a compact electric tractor"),
    "combine_harvester": (15000, 350, 6000, 30, "AWD", 6.0, "an electric combine"),
    "forklift": (4000, 20, 300, 18, "FWD", 2.0, "an electric forklift with its counterweight"),
    "riding_mower": (250, 8, 60, 12, "RWD", 1.0, "a ride-on mower"),
    "taxi": (1800, 150, 380, 175, "RWD", 0.58, "a taxi sedan"),
    "excavator": (14000, 120, 8000, 6, "AWD", 6.0, "a tracked excavator"),
}


def phys(k, x):
    L, W, H = x["size_m"]
    if k in PHYS_AS:
        m, kw, nm, top, drive, cda, like = PHYS_AS[k]
        src = "approx. specs of " + like
    else:
        dens, wkg, top, drive, cd = PHYS_CAT.get(x["category"], (110, 40, 100, "RWD", 0.5))
        m = max(5.0, dens * L * W * H)
        kw = wkg * m / 1000.0
        nm = max(5.0, kw * 1000.0 / (0.35 * top / 3.6 / 0.34) * 0.34 / 9.0)      # peak torque at the motor (a 9:1 gear)
        cda = cd * W * H * 0.85
        src = "scaled from size and category (%s)" % x["category"]
    r = 0.34 if m > 400 else (0.33 if m > 50 else 0.3)
    if m > 6000:
        r = 0.5
    # the gear: the motor's top speed (~15,000 rpm for cars, less for heavy motors) reaches the top speed
    rpm_max = 15000.0 if m < 5000 else 6000.0
    gear = max(1.0, rpm_max * 2 * 3.14159 / 60.0 * r / max(1.0, top / 3.6)) if kw > 0.5 else 1.0
    return {"mass_kg": round(m), "power_kw": round(kw, 2), "torque_nm": round(nm), "gear": round(gear, 2), "wheel_r": r,
            "top_kmh": top, "drive": drive, "cda": round(cda, 2), "source": src}


def main():
    places = json.load(open(os.path.join(CH, "npc_places.json")))["types"]
    units = json.load(open(os.path.join(CH, "npc_place_index.json")))["units"]
    people = json.load(open(os.path.join(CH, "npc_lives.json")))["people"]
    settle = json.load(open(os.path.join(CH, "npc_settlements.json")))["settlements"]
    occ = json.load(open(os.path.join(CH, "npc_traits.json")))["tables"]["occupations"]
    roles = {r["id"] for r in json.load(open(os.path.join(ROOT, "research", "roles", "roles.json")))["roles"]}
    errs = []
    for k, x in V.items():
        errs += ["%s: place %s" % (k, p) for p in x["per_place"] if p not in places]
        errs += ["%s: occupation %s" % (k, o) for o in x["occupations"] if o not in occ]
        errs += ["%s: role %s" % (k, r) for r in x["roles"] if r not in roles]
    by_type = Counter(u["type"] for u in units)
    hhn, households = household_fleet(people, settle)
    place_fleet(units, V)
    with open(os.path.join(CH, "npc_fleet.json"), "w") as f:
        json.dump({"_about": "Every road vehicle with a model and where it lives: household cars with their drivers (as counted in npc_vehicles.json), "
                             "work vehicles at their places, rounds and hours for those that go about. Generated by tools/places/make_vehicles.py; "
                             "NpcTraffic reads it.", "vehicles": FLEET}, f)
    towns = {u["settlement"] for u in units}
    resort_towns = sum(1 for t in towns if settle.get(t) == "lake_resort")
    for k, x in V.items():
        x["phys"] = phys(k, x)
    for k, x in V.items():
        n = sum(by_type.get(p, 0) * c for p, c in x["per_place"].items()) + x["per_town"] * len(towns)
        n += hhn.get(k, 0)
        if k == "sightseeing_trolley":
            n += resort_towns * 0.5
        if x["category"] == "rail":
            n += {"passenger_train": 2, "freight_locomotive": 2, "boxcar": 12, "covered_hopper": 0, "tank_car": 6, "flatcar": 6, "reefer_car": 0, "hi_rail_truck": 1}.get(k, 0)
        x["station_count"] = int(round(n))
        x["station_count_note"] = "place units x per_place" + (" + per_town x %d towns" % len(towns) if x["per_town"] else "") + (" + households (npc_lives)" if k in hhn else "") + (" + one rail line" if x["category"] == "rail" else "")
    out = {"_about": "Vehicle types: the contract between the procedural engine and the vehicle models (like npc_places.json for buildings). "
                     "Types and roles, not designs; the station's design language (pod, van, aerostat) sets the look. station_count: how many "
                     "the present station needs, from the baked places and residents. Generated by tools/places/make_vehicles.py; "
                     "research/lives/06_vehicles.md.", "version": 1, "vehicles": V}
    with open(os.path.join(CH, "npc_vehicles.json"), "w") as f:
        json.dump(out, f, indent=1)
    cats = []
    for x in V.values():
        if x["category"] not in cats:
            cats.append(x["category"])
    title = {"household": "Household vehicles (people's own)", "mobility": "Personal mobility aids", "cart": "Hand-pushed carts at places",
             "transit": "Public transport", "rail": "Rail (the station's rail line)", "commercial": "Commercial and trade", "farm": "Farm",
             "industry": "Construction and industry", "emergency": "Emergency", "civic": "Civic and municipal", "water": "Water",
             "amusement": "Amusement and leisure", "station": "The station"}
    pri = Counter(x["priority"] for x in V.values())
    exists = [k for k, x in V.items() if x["status"].startswith("exists")]
    md = ["# 6. Vehicles: everything the engine needs a model for", "",
          "Generated by `tools/places/make_vehicles.py` alongside `godot_project/remake/characters/npc_vehicles.json`. **%d vehicle types** in %d groups. "
          "Every place, occupation and role named is checked against the building types, the occupations table and `research/roles/roles.json` (%s)." % (
              len(V), len(cats), "all valid" if not errs else "PROBLEMS: " + "; ".join(errs)), "",
          "As with the buildings, these are **types and roles, not designs**. The station's design language (the existing pod, van and aerostat) sets the look in the game bible; the models come after, built to these slots: size, seats, the states they must show, their variants, and what the people using them must be able to do (animation clips).", "",
          "**Priority 1** means the engine already asks for it: a commute mode, a place's machinery, a trait, a job. Priority 2 comes with the next systems (deliveries, emergencies, harbours, the rail line). Priority 3 adds variety and colour. "
          "Counts by priority: 1: %d, 2: %d, 3: %d. **Already modelled:** %s." % (pri[1], pri[2], pri[3], ", ".join("`%s` (%s)" % (k, V[k]["status"][8:]) for k in exists)), "",
          "**Station count** is how many the present station (%d households, %d residents, %d place units) needs. It combines the place units' fleets (`per_place` × the number of units of each type), the households' own vehicles (drawn per household from the residents' car access, commute, age, family, finances, farm or trade, and resort town), and one rail line." % (
              households, len(people), len(units)), ""]
    tot = 0
    for c in cats:
        rows = [(k, x) for k, x in V.items() if x["category"] == c]
        sub = sum(x["station_count"] for _, x in rows)
        tot += sub
        md += ["## %s (%d types, %d on the station)" % (title.get(c, c), len(rows), sub), "",
               "| vehicle | pri | size L×W×H m, seats | who / where | station count | states | npc actions |", "|---|---|---|---|---|---|---|"]
        for k, x in rows:
            where = x["who"]
            if x["per_town"]:
                where += " · %g per town" % x["per_town"]
            if x["per_place"]:
                where += " · at: " + ", ".join("%s %g" % (p, n) for p, n in x["per_place"].items() if n)
            if x["occupations"]:
                where += " · jobs: " + ", ".join(x["occupations"])
            if x["note"]:
                where += " · *%s*" % x["note"]
            name = "**%s** `%s`%s" % (x["name"], k, " (%s)" % x["status"] if x["status"] != "needed" else "")
            md.append("| %s | %d | %s, %d | %s | %d | %s | %s |" % (name, x["priority"], "×".join("%g" % s for s in x["size_m"]), x["seats"], where,
                                                                  x["station_count"], ", ".join(x["states"]), ", ".join(x["npc_actions"]) or "–"))
        md.append("")
    md += ["## Totals", "", "%d vehicles on the present station across %d types. Household cars: %d, for %d households (%.2f per household; the US average is about 1.9 including households with none). Bicycles: %d adult and %d children's." % (
        tot, len(V), sum(hhn[k] for k in ("city_car", "sedan", "station_wagon", "crossover_suv", "full_size_suv", "minivan", "pickup_truck", "sports_car", "convertible", "luxury_sedan")),
        households, sum(hhn[k] for k in ("city_car", "sedan", "station_wagon", "crossover_suv", "full_size_suv", "minivan", "pickup_truck", "sports_car", "convertible", "luxury_sedan")) / max(1, households),
        hhn["bicycle"], hhn["child_bicycle"]), "",
        "## Models (2026-09-30)",
        "- **Every type above has a model**: `godot_project/remake/vehicles/<id>.glb`, built from Grok's 2D reference images by the `ssc-asset` skill (`tools/assets`, `remake/blender/kit`): solid hulls with rigged wheels, open frames as cut-out panels, and the five people ride inside (tram, transit bus, school bus, train car, sightseeing trolley) hollow with interiors fitted from Grok's cutaway, plan and aisle views, at least 2.2 m floor to ceiling. The bicycle is hand-built (`remake/blender/vehicles/bicycle.py`).",
        "- **Interiors:** the other enclosed vehicles have interiors **extrapolated** from their exteriors (`remake/blender/kit/cabin.py`: glazed windows, seats to the seat count, dash, wheel on the left, a 1970s colour scheme); `tools/assets/INTERIORS.md` lists how each was made and which go back to Grok if we don't like them.",
        "- **In use:** NPC cyclists (NpcBike, NpcAnimator.ride) and parked bicycles the player rides in person (RemakeBicycle); trams on three road lines and the Ring Line train (`remake/scripts/transit`) with seated and standing passengers, which the player can board. The tram is articulated in seven bodies with bellows and colliders, turning round on paved trolley loops at the ends of its lines.",
        "- **Traffic** (`NpcTraffic`, `remake/characters/npc_traffic.gd`; the fleet in `npc_fleet.json`, written here): every household car with its driver and every work vehicle at its place. A car is parked by its driver's home until their first car trip (NpcLife), driven along the right-hand lane by them for as long as the drive takes, then parked by wherever they went; work vehicles park at their places, and mail, deliveries, police, refuse, street sweeping, taxis and the like do rounds through their town in their hours. Parked: in the kerbside parking lane of a main road, else just off the road past the pavement, clear of buildings and of each other. Streamed within 160 m of the player, each with a collider.",
        "",
        "## What the engine still needs to use them",
        "- **Parking:** `groundcars.json` parks pods and vans kerbside. Household cars belong in driveways, garages and kerbs by their homes; work vehicles belong in yards, bays and docks. That's a parking-slot contract on the building shells.",
        "- **Stops and stations:** bus and tram stops, the platform, the ferry terminal, bike racks, taxi ranks: street-furniture contracts.",
        "- **Clips:** getting in and out, riding (bike, scooter, motorcycle, mower), pushing (stroller, cart, wheelchair, gurney), boarding. `npc_actions` lists them per vehicle.",
        "- **Liveries** are procedural like shop signs: the business name from the place unit, the town's seal, the carrier's colours.",
        "- **Condition** follows the owner's `finances` (new, kept, worn, beater), and a few derelicts sit in yards (`money_reasons` laid_off, `finances` struggling).",
        "- **Canon: every vehicle is electric or pedal-powered**; nothing burns fuel. Road vehicles charge at home, at charging stops (`charge_stop`, which replaces the gas station), at depots and yards; trams charge at their stops. Trams run on roads.",
        "- **Not listed, on purpose:** fuel tankers; snowplows and snowmobiles (the station's climate is controlled); aircraft (aerostats fly instead); horses and carriages (the game bible may add them).",
        "- **A gap in the places:** the registry's police/fire type matched only one civic building on the whole station, so emergency and public-works vehicles are also counted **per town** (%d towns; small American towns each keep a fire company, mostly volunteer). The places bake should give every town a fire station and a public-works yard." % len(towns),
        "- **Station facilities** (port, transit station, air plant...) have no buildings on the map yet, so their vehicles count 0 today; the list is ready for them.",
        "- **Game-bible decisions:** bus, tram or both; how people reach the axis and the port (the spoke elevator); how much freight flies by aerostat; whether a car dealership exists (there is no place type for one yet)."]
    with open(os.path.join(ROOT, "research", "lives", "06_vehicles.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("%d vehicle types, %d groups; priorities %s; station total %d; problems: %s" % (len(V), len(cats), dict(pri), tot, errs or "none"))


if __name__ == "__main__":
    main()
