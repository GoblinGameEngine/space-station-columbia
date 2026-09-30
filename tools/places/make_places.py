#!/usr/bin/env python3
"""The building-types contract: what kinds of place exist, what each needs from a building shell,
what belongs inside (as categories, never specific models), who works there, who visits and why.

    python3 tools/places/make_places.py

Writes godot_project/remake/characters/npc_places.json (the engine reads it) and
research/lives/01_building_types.md (to read). A place's purpose is procedural: a storefront
becomes a grocery or a bar by its signage and contents, allocated per settlement from what the town
needs (bake_places.py), the catalog's current signage only a hint. The contents lists are the
contract the models will be built to (the user's order: engine, then game bible, then models).
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

SHELLS = {
    "storefront": "a ground-floor commercial unit behind a shop window (catalog storefront slot)",
    "upper_apartment": "flats over shops (catalog upper_use apartments)",
    "upper_office": "offices over shops (catalog upper_use offices)",
    "upper_hall": "a lodge or meeting hall upstairs (catalog upper_use lodge_hall)",
    "house": "a detached or row dwelling",
    "civic_hall": "a public building (town hall, courthouse, post office, library...)",
    "church": "a church building",
    "school": "a school building",
    "hotel": "a hotel or tavern-hotel",
    "motel": "a motel",
    "restaurant_building": "a free-standing restaurant",
    "industrial_shed": "a factory, mill, works or plant building",
    "waterfront_works": "cannery, fish house, boatyard, ice house, net loft",
    "warehouse": "a warehouse",
    "farmstead": "a farm's house, barns, silos and sheds",
    "kiosk": "a small booth or stand",
    "pavilion": "an open-sided shelter, bandstand or beach pavilion",
    "big_box": "a large single-storey store",
    "strip_unit": "a unit in a strip of shops",
    "tower": "a lighthouse, lifeguard tower or water tower",
    "station_module": "a purpose-built station facility (future buildings)",
}

# type id: name, category, shells, jobs {occupation: n}, hours [open, close, days], visits [(purpose,
# per_week, who, dwell_min)], third_place, price 0-3, per1000 (settlement demand; 0 = allocate from
# hints/special), fixtures, stock, machinery, signage, hints (catalog storefront types / uses),
# addictions, roles (roles.json ids)
T = {}


def pt(id, name, cat, shells, jobs, hours, visits, third=False, price=1, per1000=0.0, fixtures=(), stock=(), machinery=(),
       signage="fascia", hints=(), addictions=(), roles=(), station=False, note=""):
    T[id] = dict(name=name, category=cat, shells=list(shells), jobs=jobs, hours=dict(open=hours[0], close=hours[1], days=hours[2]),
                 visits=[dict(purpose=p, per_week=w, who=who, dwell_min=d) for p, w, who, d in visits], third_place=third,
                 price=price, per1000=per1000, contents=dict(fixtures=list(fixtures), stock=list(stock), machinery=list(machinery)),
                 signage=signage, hints=list(hints), addictions=list(addictions), roles=list(roles), station=station, note=note)


SF = ["storefront", "strip_unit"]
WK = "mon-sat"
ALL = "daily"
ANY = "true"
ADULT = "age >= 18"
# -- food and drink
pt("grocery", "Grocery", "food", SF + ["big_box"], {"shop_clerk": 4, "shopkeeper": 1, "cook": 1}, ["07:00", "21:00", ALL],
   [("groceries", 1.0, ADULT, 25)], price=1, per1000=0.8, fixtures=["checkout_counter", "shelving_aisles", "chiller_cases", "freezer_cases", "produce_bins", "baskets_carts"],
   stock=["produce", "canned_goods", "dairy", "bread", "meat", "household_goods"], signage="fascia", hints=["grocery", "dry_goods", "variety_store"], roles=["shopkeeper", "retail_clerk", "cashier", "stocker"])
pt("bakery", "Bakery", "food", SF, {"baker": 2, "shop_clerk": 1}, ["06:00", "15:00", WK], [("bread", 0.6, ADULT, 8)], price=1, per1000=0.3,
   fixtures=["display_case", "counter", "bread_racks", "ovens_back"], stock=["bread", "pastries", "cakes"], machinery=["deck_oven", "mixer", "proofer"], hints=["bakery"], roles=["cook"])
pt("butcher", "Butcher", "food", SF, {"shopkeeper": 1, "shop_clerk": 1}, ["08:00", "18:00", WK], [("meat", 0.3, ADULT, 8)], price=2, per1000=0.15,
   fixtures=["chilled_counter", "hooks_rail", "block_table"], stock=["meat", "sausages"], machinery=["band_saw", "grinder", "walk_in_cooler"], hints=["butcher"])
pt("fish_market", "Fish market", "food", SF + ["waterfront_works"], {"shopkeeper": 1, "fisher": 1}, ["06:00", "14:00", WK], [("fish", 0.2, ADULT, 8)], price=1, per1000=0.1,
   fixtures=["ice_counter", "scales", "sink"], stock=["fish", "shellfish"], hints=["fish_market", "raw_bar"])
pt("cafe", "Café", "food", SF + ["pavilion"], {"cook": 1, "waiter": 2}, ["06:30", "17:00", ALL], [("coffee", 0.8, "age >= 14", 35)], third=True, price=1, per1000=0.8,
   fixtures=["counter", "espresso_machine", "tables_chairs", "pastry_case", "menu_board"], stock=["coffee", "pastries", "sandwiches"], hints=["cafe", "ice_cream", "taffy_fudge"], addictions=["caffeine"], roles=["cook", "waiter", "regular"])
pt("diner", "Diner", "food", SF + ["restaurant_building"], {"cook": 2, "waiter": 3}, ["06:00", "21:00", ALL], [("meal", 0.5, ANY, 45)], third=True, price=1, per1000=0.4,
   fixtures=["counter_stools", "booths", "kitchen_line", "pie_case"], stock=["plates", "menus"], machinery=["griddle", "fryer"], hints=["diner", "pizza_slice", "pizza"], roles=["cook", "waiter", "regular"])
pt("restaurant", "Restaurant", "food", SF + ["restaurant_building", "hotel"], {"cook": 3, "waiter": 4, "bartender": 1}, ["11:00", "22:00", ALL], [("dinner_out", 0.25, ADULT, 75)], price=2, per1000=0.3,
   fixtures=["dining_tables", "bar_counter", "kitchen_line", "host_stand"], stock=["tableware", "wine"], machinery=["range", "walk_in_cooler"], hints=["seafood_restaurant", "restaurant"])
pt("bar", "Bar / tavern", "drink", SF + ["hotel"], {"bartender": 2, "waiter": 1}, ["15:00", "01:00", ALL], [("drinks", 0.4, "age >= 21", 90)], third=True, price=1, per1000=0.6,
   fixtures=["bar_counter", "stools", "back_bar_shelves", "booths", "jukebox", "dartboard"], stock=["beer", "spirits", "wine"], hints=["bar", "tavern_hotel", "brewpub", "wine_bar", "pool_hall"],
   addictions=["alcohol", "gambling"], roles=["bartender", "regular", "town_drunk"])
pt("liquor_store", "Liquor store", "retail", SF, {"shop_clerk": 2}, ["10:00", "22:00", ALL], [("liquor", 0.1, "age >= 21", 6)], price=1, per1000=0.2,
   fixtures=["counter", "shelving", "cooler"], stock=["spirits", "beer", "wine", "lottery_tickets"], hints=[], addictions=["alcohol", "gambling", "nicotine"])
# -- retail
pt("drug_store", "Pharmacy / drug store", "health", SF, {"pharmacist": 1, "shop_clerk": 2}, ["08:00", "21:00", ALL], [("pharmacy", 0.2, ANY, 12)], price=1, per1000=0.3,
   fixtures=["pharmacy_counter", "shelving_aisles", "checkout_counter"], stock=["medicines", "toiletries", "cosmetics", "snacks"], hints=["drug_store"], addictions=["opioids", "sedatives", "nicotine"], roles=["pharmacist"])
pt("hardware", "Hardware store", "retail", SF + ["big_box"], {"shopkeeper": 1, "shop_clerk": 2}, ["08:00", "18:00", WK], [("hardware", 0.2, ADULT, 15)], price=1, per1000=0.2,
   fixtures=["counter", "pegboard_walls", "bins", "key_cutting_bench"], stock=["tools", "paint", "fasteners", "keys", "garden"], machinery=["key_cutter", "paint_shaker"], hints=["hardware", "feed_seed", "auto_parts"])
pt("clothing", "Clothing store", "retail", SF, {"shopkeeper": 1, "shop_clerk": 2}, ["10:00", "18:00", WK], [("clothes", 0.1, "age >= 12", 25)], price=2, per1000=0.3,
   fixtures=["clothing_racks", "fitting_rooms", "counter", "mannequins"], stock=["clothing", "shoes", "accessories"], hints=["clothing", "beachwear", "t_shirts", "shoe_store", "surf_shop"], addictions=["shopping"])
pt("variety_store", "Variety / general store", "retail", SF, {"shopkeeper": 1, "shop_clerk": 1}, ["08:00", "20:00", ALL], [("sundries", 0.3, "age >= 8", 12)], price=1, per1000=0.3,
   fixtures=["counter", "shelving", "candy_rack"], stock=["sundries", "toys", "snacks", "newspapers", "lottery_tickets"], hints=["variety_store", "dry_goods", "souvenir", "marina_store"], addictions=["gambling", "nicotine"])
pt("thrift_store", "Thrift store", "retail", SF, {"shop_clerk": 2}, ["10:00", "17:00", WK], [("thrift", 0.08, ADULT, 25)], price=0, per1000=0.1,
   fixtures=["racks", "bins", "counter"], stock=["used_clothing", "used_goods"], hints=["thrift_store"])
pt("bookstore", "Bookstore", "retail", SF, {"shopkeeper": 1}, ["10:00", "18:00", WK], [("books", 0.08, "age >= 10", 25)], third=True, price=1, per1000=0.1,
   fixtures=["bookshelves", "reading_chairs", "counter"], stock=["books", "magazines"], hints=["bookstore", "music_store", "video_rental"])
pt("jeweler", "Jeweller", "retail", SF, {"shopkeeper": 1}, ["10:00", "17:00", WK], [("jewellery", 0.01, ADULT, 20)], price=3, per1000=0.05,
   fixtures=["display_cases", "safe", "counter"], stock=["jewellery", "watches"], hints=["jeweler"])
pt("florist", "Florist", "retail", SF, {"shopkeeper": 1}, ["09:00", "17:00", WK], [("flowers", 0.03, ADULT, 10)], price=2, per1000=0.08,
   fixtures=["buckets", "cooler", "work_table"], stock=["flowers", "plants"], hints=["florist"])
pt("furniture", "Furniture / appliance store", "retail", SF + ["big_box"], {"shop_clerk": 2}, ["10:00", "18:00", WK], [("furniture", 0.01, ADULT, 30)], price=2, per1000=0.05,
   fixtures=["showroom_floor"], stock=["furniture", "appliances"], hints=["furniture", "appliance_repair"])
pt("sporting_goods", "Sporting goods / outfitter", "retail", SF + ["kiosk"], {"shop_clerk": 2}, ["09:00", "18:00", WK], [("gear", 0.04, "age >= 10", 20)], price=2, per1000=0.08,
   fixtures=["racks", "counter", "gun_case_optional"], stock=["sports_gear", "fishing_tackle", "bikes"], hints=["sporting_goods", "bike_rental", "surf_shop", "bait"])
pt("gas_station", "Gas station / convenience", "retail", ["kiosk", "strip_unit", "storefront"], {"shop_clerk": 2}, ["05:00", "23:00", ALL], [("fuel", 0.4, "car_access != 'none'", 8)], price=1, per1000=0.4,
   fixtures=["pumps", "counter", "cooler", "snack_racks"], stock=["fuel", "snacks", "cigarettes", "lottery_tickets", "energy_drinks"], hints=["gas_station"], addictions=["nicotine", "gambling", "caffeine"])
pt("newsagent", "Newsstand / tobacconist", "retail", ["kiosk", "storefront"], {"shop_clerk": 1}, ["06:00", "18:00", ALL], [("papers", 0.4, ADULT, 4)], price=0, per1000=0.1,
   fixtures=["counter", "news_racks"], stock=["newspapers", "magazines", "tobacco", "lottery_tickets"], hints=["kiosk"], addictions=["nicotine", "gambling"])
# -- services
pt("barber", "Barber", "service", SF, {"barber": 2}, ["08:00", "18:00", WK], [("haircut", 0.25, "sex == 'male'", 30)], third=True, price=1, per1000=0.25,
   fixtures=["barber_chairs", "mirrors", "waiting_bench", "pole"], stock=["hair_products"], hints=["barber"], roles=["barber", "regular"])
pt("beauty_salon", "Beauty salon", "service", SF, {"barber": 2}, ["09:00", "19:00", WK], [("hair", 0.2, "sex == 'female'", 60)], third=True, price=2, per1000=0.25,
   fixtures=["styling_chairs", "wash_basins", "dryers", "mirrors"], stock=["hair_products", "nail_polish"], hints=["beauty_salon"], roles=["barber", "regular"])
pt("laundromat", "Laundromat", "service", SF, {"janitor": 1}, ["06:00", "22:00", ALL], [("laundry", 0.3, ADULT, 60)], third=True, price=0, per1000=0.15,
   fixtures=["washers", "dryers", "folding_tables", "benches"], machinery=["washers", "dryers"], hints=["laundromat"])
pt("bank", "Bank", "service", SF + ["civic_hall"], {"banker": 3, "clerk": 2}, ["09:00", "16:00", "mon-fri"], [("banking", 0.15, ADULT, 12)], price=0, per1000=0.2,
   fixtures=["teller_windows", "vault", "desks", "waiting_line"], hints=["bank"], roles=["banker"])
pt("insurance_office", "Insurance / real-estate office", "service", SF + ["upper_office"], {"agent": 2, "clerk": 1}, ["09:00", "17:00", "mon-fri"], [("insurance", 0.02, ADULT, 30)], price=0, per1000=0.3,
   fixtures=["desks", "filing_cabinets", "listing_boards"], hints=["insurance_office", "real_estate"], roles=["insurance_agent", "real_estate_agent"])
pt("law_office", "Law office", "service", SF + ["upper_office"], {"lawyer": 2, "clerk": 1}, ["09:00", "17:00", "mon-fri"], [("legal", 0.005, ADULT, 45)], price=3, per1000=0.15,
   fixtures=["desks", "bookshelves", "conference_table"], hints=["law_office"], roles=["lawyer"])
pt("print_shop", "Print shop / newspaper", "service", SF, {"editor": 1, "clerk": 2}, ["08:00", "17:00", "mon-fri"], [("printing", 0.01, ADULT, 15)], price=1, per1000=0.08,
   fixtures=["counter", "type_cases", "desks"], machinery=["printing_press", "folder"], hints=["print_shop", "newspaper"], roles=["journalist"])
pt("repair_shop", "Repair shop (shoes, appliances)", "service", SF, {"mechanic": 1}, ["09:00", "17:00", WK], [("repair", 0.02, ADULT, 10)], price=1, per1000=0.1,
   fixtures=["workbench", "counter", "parts_shelves"], machinery=["stitcher", "tool_board"], hints=["shoe_repair", "appliance_repair"])
pt("auto_repair", "Garage / auto repair", "service", SF + ["industrial_shed"], {"mechanic": 3}, ["07:30", "17:30", WK], [("car_service", 0.03, "car_access != 'none'", 60)], price=2, per1000=0.2,
   fixtures=["service_bays", "counter", "tire_racks"], machinery=["car_lift", "air_compressor", "tool_chests"], hints=["auto_repair"], roles=["mechanic"])
pt("funeral_home", "Funeral home", "service", SF + ["house"], {"clerk": 1}, ["09:00", "17:00", ALL], [], price=3, per1000=0.03,
   fixtures=["viewing_room", "chapel_chairs", "office"], hints=["funeral_home"])
# -- health
pt("doctor_office", "Doctor's office / clinic", "health", SF + ["upper_office", "civic_hall"], {"doctor": 1, "nurse": 2, "clerk": 1}, ["08:00", "17:00", "mon-fri"], [("doctor", 0.08, ANY, 40)], price=2, per1000=0.3,
   fixtures=["waiting_room", "exam_rooms", "reception_desk"], stock=["medical_supplies"], hints=["doctor_office"], roles=["physician", "nurse"])
pt("dentist", "Dentist", "health", SF + ["upper_office"], {"dentist": 1, "nurse": 1}, ["08:00", "17:00", "mon-fri"], [("dentist", 0.04, ANY, 45)], price=2, per1000=0.15,
   fixtures=["dental_chair", "waiting_room"], machinery=["dental_unit", "x_ray"], hints=["dentist"])
pt("hospital", "Hospital", "health", ["civic_hall"], {"doctor": 8, "nurse": 25, "care_aide": 10, "janitor": 4, "clerk": 5, "cook": 3}, ["00:00", "24:00", ALL], [("hospital", 0.01, ANY, 120)], price=3,
   fixtures=["wards", "emergency_bay", "operating_room"], machinery=["imaging", "monitors"], hints=["Hospital"], roles=["physician", "nurse", "emt"])
pt("care_home", "Care home", "health", ["house", "civic_hall"], {"care_aide": 6, "nurse": 2, "cook": 1}, ["00:00", "24:00", ALL], [("visit_elder", 0.2, ADULT, 60)], price=2,
   fixtures=["bedrooms", "lounge", "dining_room"], hints=[], roles=["home_health_aide"])
# -- civic
pt("post_office", "Post office", "civic", ["civic_hall", "storefront"], {"postal_worker": 4, "clerk": 1}, ["08:00", "17:00", WK], [("post", 0.25, ADULT, 12)], price=0, per1000=0.2,
   fixtures=["counter", "po_boxes", "sorting_tables"], stock=["parcels", "stamps"], hints=["Post Office", "post_office"], roles=["postal_worker"])
pt("town_hall", "Town hall / council", "civic", ["civic_hall"], {"clerk": 5}, ["09:00", "17:00", "mon-fri"], [("civic_business", 0.02, ADULT, 30)], price=0,
   fixtures=["council_chamber", "clerk_counter", "offices"], hints=["City Hall", "Town Hall", "city_hall", "town_hall"], roles=["mayor", "council_member", "administrator"])
pt("courthouse", "Courthouse", "civic", ["civic_hall"], {"lawyer": 2, "clerk": 3, "police": 1}, ["09:00", "17:00", "mon-fri"], [("court", 0.002, ADULT, 120)], price=0,
   fixtures=["courtroom", "judge_bench", "holding_cell"], hints=["Courthouse"], roles=["judge", "lawyer"])
pt("library", "Library", "civic", ["civic_hall"], {"librarian": 2, "clerk": 1}, ["10:00", "19:00", WK], [("library", 0.12, "age >= 5", 45)], third=True, price=0, per1000=0.2,
   fixtures=["bookstacks", "reading_tables", "circulation_desk", "computers"], stock=["books", "archives"], hints=["Library", "Carnegie Library"], roles=["librarian"])
pt("police_fire", "Police / fire station", "civic", ["civic_hall"], {"police": 4, "firefighter": 4}, ["00:00", "24:00", ALL], [], price=0,
   fixtures=["front_desk", "engine_bay", "cells", "bunk_room"], machinery=["fire_engine", "patrol_car"], hints=["Fire / Police"], roles=["police", "firefighter", "marshal"])
pt("harbormaster", "Harbormaster / coast guard", "civic", ["civic_hall", "tower"], {"dock_worker": 2, "clerk": 1}, ["06:00", "20:00", ALL], [], price=0,
   fixtures=["office", "radio_desk", "chart_table"], machinery=["radio", "boats"], hints=["Harbormaster", "Coast Guard", "Ferry Terminal"], roles=["port_master"])
pt("community_hall", "Community / lodge hall", "civic", ["upper_hall", "civic_hall"], {"janitor": 1}, ["18:00", "23:00", ALL], [("meeting", 0.1, ADULT, 120)], third=True, price=0,
   fixtures=["hall_chairs", "stage", "kitchen"], hints=["lodge_hall", "Convention Hall", "Opera House", "Visitor Center", "Oceanfront Visitor Ctr.", "Yacht Club"], roles=["club_president", "festival_organiser"])
pt("school", "School", "education", ["school"], {"teacher": 12, "care_aide": 3, "janitor": 2, "cook": 2, "clerk": 1}, ["08:00", "15:30", "mon-fri"], [("school", 5.0, "occupation == 'student'", 420)], price=0,
   fixtures=["classrooms", "desks", "chalkboards", "gym", "cafeteria"], stock=["books", "supplies"], roles=["teacher", "teacher_aide"])
pt("college", "College", "education", ["school", "civic_hall"], {"teacher": 20, "librarian": 2, "clerk": 4, "janitor": 3, "cook": 3}, ["08:00", "21:00", "mon-fri"],
   [("classes", 4.0, "occupation == 'university_student'", 240)], third=True, price=0, fixtures=["lecture_halls", "labs", "library", "quad_benches"], stock=["books"],
   machinery=["lab_equipment"], roles=["teacher"], note="the largest school of a college town (bake_places.py)")
pt("childcare", "Childcare centre", "education", SF + ["house"], {"care_aide": 3}, ["07:00", "18:00", "mon-fri"], [("childcare", 5.0, "occupation == 'preschool'", 480)], price=2, per1000=0.2,
   fixtures=["play_room", "nap_mats", "cubbies"], stock=["toys"], roles=["childcare_worker"])
pt("church", "Church", "faith", ["church"], {"pastor": 1}, ["08:00", "20:00", ALL], [("worship", 1.0, "congregant", 75)], third=True, price=0,
   fixtures=["pews", "altar", "pulpit", "organ"], stock=["hymnals"], roles=["clergy", "church_elder", "choir_director"])
# -- leisure
pt("movie_theater", "Cinema", "leisure", SF, {"shop_clerk": 2}, ["14:00", "23:00", ALL], [("film", 0.1, "age >= 8", 130)], price=1, per1000=0.1,
   fixtures=["auditorium_seats", "screen", "concession_counter"], machinery=["projector"], hints=["movie_theater"])
pt("arcade", "Arcade / games hall", "leisure", ["storefront", "kiosk", "pavilion"], {"shop_clerk": 1}, ["11:00", "23:00", ALL], [("games", 0.12, "age >= 10", 60)], price=1, per1000=0.08,
   fixtures=["cabinets", "change_counter", "prize_counter"], machinery=["arcade_cabinets", "claw_machines", "slot_style_machines"], hints=["arcade", "games"], addictions=["gaming", "gambling"])
pt("amusement", "Amusement ride / stand", "leisure", ["kiosk", "pavilion", "tower"], {"shop_clerk": 1}, ["10:00", "22:00", "seasonal"], [("ride", 0.05, "age >= 5", 20)], price=1,
   fixtures=["ticket_booth"], machinery=["ride_machinery"], hints=["ride", "carousel", "ferris_wheel", "go_karts"])
pt("food_stand", "Food / souvenir stand", "food", ["kiosk"], {"shop_clerk": 1}, ["10:00", "20:00", "seasonal"], [("snack", 0.2, ANY, 5)], price=1,
   fixtures=["service_window", "counter"], stock=["snacks", "drinks", "souvenirs"], hints=["food", "souvenir", "stand", "bait"])
pt("park_pavilion", "Bandstand / pavilion", "leisure", ["pavilion"], {}, ["00:00", "24:00", ALL], [("outing", 0.15, ANY, 45)], third=True, price=0,
   fixtures=["benches", "stage"], hints=["bandstand", "shelter", "ticket", "cafe"])
pt("gym", "Gym / fitness", "leisure", SF + ["big_box"], {"shop_clerk": 1}, ["05:00", "22:00", ALL], [("workout", 0.3, "age >= 15", 60)], price=1, per1000=0.1,
   fixtures=["weights", "mats", "lockers"], machinery=["treadmills", "machines"], hints=[])
# -- lodging
pt("hotel", "Hotel", "lodging", ["hotel"], {"hotel_worker": 6, "cook": 2, "waiter": 2, "janitor": 2, "clerk": 1}, ["00:00", "24:00", ALL], [], price=2,
   fixtures=["lobby_desk", "guest_rooms", "dining_room"], hints=["tavern_hotel"])
pt("motel", "Motel", "lodging", ["motel"], {"hotel_worker": 3, "janitor": 1}, ["00:00", "24:00", ALL], [], price=1,
   fixtures=["office_desk", "guest_rooms", "ice_machine"], hints=["motel"])
# -- industry (the machinery lists are what the factories are empty of today)
pt("factory", "Factory", "industry", ["industrial_shed"], {"factory_hand": 30, "mechanic": 3, "clerk": 3, "janitor": 2, "driver": 3}, ["06:00", "22:00", "mon-fri"], [], price=0,
   fixtures=["shop_floor", "offices", "loading_dock", "time_clock", "break_room"], machinery=["assembly_line", "presses", "conveyors", "forklifts", "paint_booth"], hints=["factory"], roles=["factory_worker", "union_steward"])
pt("machine_works", "Machine works", "industry", ["industrial_shed"], {"factory_hand": 20, "mechanic": 4, "clerk": 2}, ["06:00", "18:00", "mon-fri"], [], price=0,
   fixtures=["shop_floor", "tool_crib", "loading_dock"], machinery=["lathes", "milling_machines", "drill_presses", "welding_bays", "overhead_crane"], hints=["machine_works"])
pt("mill", "Flour / feed mill", "industry", ["industrial_shed"], {"factory_hand": 8, "driver": 2, "clerk": 1}, ["06:00", "18:00", "mon-sat"], [], price=0,
   fixtures=["bins", "bagging_floor"], machinery=["roller_mills", "sifters", "bucket_elevator", "bagging_machine"], hints=["flour_mill"])
pt("grain_elevator", "Grain elevator", "industry", ["industrial_shed", "tower"], {"factory_hand": 4, "driver": 3}, ["06:00", "20:00", "seasonal"], [], price=0,
   fixtures=["scale_house", "office"], machinery=["bucket_elevator", "augers", "grain_dryer", "truck_scale"], hints=["grain_elevator"])
pt("cannery", "Cannery", "industry", ["waterfront_works"], {"factory_hand": 25, "dock_worker": 4, "mechanic": 2}, ["05:00", "19:00", "seasonal"], [], price=0,
   fixtures=["processing_floor", "cold_store", "loading_dock"], machinery=["retorts", "sealing_line", "conveyors", "boilers"], hints=["cannery"])
pt("fish_house", "Fish house / net loft", "industry", ["waterfront_works", "warehouse"], {"fisher": 4, "dock_worker": 2}, ["04:00", "16:00", "mon-sat"], [], price=0,
   fixtures=["gutting_tables", "net_racks", "ice_bins"], machinery=["winches", "ice_maker"], hints=["fish_processing", "net_loft"])
pt("boatyard", "Boatyard", "industry", ["waterfront_works"], {"builder": 4, "mechanic": 2}, ["07:00", "17:00", "mon-sat"], [], price=0,
   fixtures=["slipway", "workshop", "boat_stands"], machinery=["travel_lift", "saws", "planer"], hints=["boat_shed"])
pt("ice_plant", "Ice house / cold store", "industry", ["waterfront_works"], {"factory_hand": 3}, ["05:00", "15:00", ALL], [], price=0,
   machinery=["ice_machines", "compressors"], hints=["ice_plant"])
pt("warehouse", "Warehouse / depot", "industry", ["warehouse", "industrial_shed"], {"dock_worker": 6, "driver": 4, "clerk": 1}, ["06:00", "18:00", "mon-fri"], [], price=0,
   fixtures=["racking", "loading_dock", "office"], machinery=["forklifts", "pallet_jacks"], hints=["depot"])
pt("construction_yard", "Builder's yard", "industry", ["industrial_shed", "warehouse"], {"builder": 10, "driver": 2}, ["07:00", "16:00", "mon-fri"], [], price=0,
   fixtures=["material_stacks", "site_office"], machinery=["mixers", "trucks", "scaffolding"], hints=[])
pt("farm", "Farm", "farm", ["farmstead"], {"farmer": 1, "farmhand": 2}, ["05:00", "20:00", ALL], [], price=0,
   fixtures=["barn_stalls", "hayloft", "milking_parlour", "silo"], machinery=["tractor", "combine", "milking_machines", "grain_dryer"], hints=["farm"], roles=["farmer", "farmhand"])
pt("lighthouse", "Lighthouse / lifeguard station", "civic", ["tower"], {"dock_worker": 1}, ["00:00", "24:00", "seasonal"], [], price=0,
   machinery=["lamp", "radio"], hints=["lighthouse", "lifeguard"])
pt("vacant", "Vacant unit", "none", SF + ["house", "industrial_shed"], {}, ["00:00", "00:00", "never"], [], price=0,
   fixtures=["dust", "for_rent_sign"], hints=["vacant_storefront", "vacant"], note="about 8% of storefronts: story hooks (who will open here?)")
# -- homes (the households generator fills these)
pt("residence", "Home", "residence", ["house", "upper_apartment", "farmstead"], {}, ["00:00", "24:00", ALL], [], price=0,
   fixtures=["kitchen", "living_room", "bedrooms"], hints=["house", "apartments"])
# -- station facilities (future buildings; research/roles/03)
for sid, name, jobs, fx, mach, roles in [
    ("life_support_plant", "Air plant", {"mechanic": 4}, ["control_room"], ["scrubbers", "electrolysis_cells", "fans"], ["air_plant_operator"]),
    ("water_works", "Water reclamation works", {"mechanic": 3}, ["control_room", "tanks"], ["filters", "distillers", "pumps"], ["water_tech"]),
    ("power_station", "Power station", {"mechanic": 3}, ["control_room"], ["switchgear", "batteries", "turbines"], ["power_tech"]),
    ("hydroponics", "Hydroponics farm", {"farmer": 3, "farmhand": 6}, ["grow_racks", "nutrient_tanks"], ["grow_lights", "pumps"], ["agronomist"]),
    ("port", "Port / docking hub", {"dock_worker": 8, "clerk": 2}, ["customs_desk", "cargo_bay", "waiting_hall"], ["cargo_lifts", "airlocks"], ["port_master", "cargo_handler", "quarantine_officer"]),
    ("admin_center", "Station administration", {"clerk": 8}, ["council_chamber", "offices"], [], ["administrator", "ombudsman"]),
    ("canteen", "Canteen", {"cook": 4, "waiter": 3}, ["long_tables", "serving_line"], ["kitchen_line"], ["cook"]),
    ("transit_station", "Transit stop / tram station", {"driver": 2}, ["platform", "benches", "timetable"], ["tram"], ["truck_driver"]),
    ("recycling_center", "Recycling centre", {"factory_hand": 6}, ["sorting_floor"], ["shredders", "compactors", "digesters"], ["recycler"]),
    ("comms_center", "Earth-link communications", {"clerk": 2}, ["booths", "mail_counter"], ["antenna_control"], ["comms_officer"]),
    ("arrival_center", "Arrival and orientation centre", {"clerk": 2}, ["waiting_hall", "desks"], [], ["arrival_coordinator"]),
    ("eva_depot", "EVA depot / airlock", {"mechanic": 2}, ["suit_lockers"], ["airlock", "suit_testers"], ["eva_tech"]),
]:
    pt(sid, name, "station", ["station_module"], jobs, ["00:00", "24:00", ALL], [], price=0, fixtures=fx, machinery=mach, roles=roles, station=True)


def main():
    occ = json.load(open(os.path.join(ROOT, "godot_project", "remake", "characters", "npc_traits.json")))["tables"]["occupations"]
    roles = {r["id"] for r in json.load(open(os.path.join(ROOT, "research", "roles", "roles.json")))["roles"]}
    bad_jobs = sorted({o for t in T.values() for o in t["jobs"] if o not in occ})
    bad_roles = sorted({r for t in T.values() for r in t["roles"] if r not in roles})
    out = {"_about": "Building types: the contract between the procedural engine and the buildings/models. A place's purpose "
                     "is procedural (signage + contents), allocated per settlement from demand; catalog signage is a hint. "
                     "contents = categories/slots the models will be built to, never specific models. Generated by "
                     "tools/places/make_places.py; read by NpcPlaces/NpcLife. research/lives/01_building_types.md",
           "version": 1, "shells": SHELLS, "types": T}
    with open(os.path.join(ROOT, "godot_project", "remake", "characters", "npc_places.json"), "w") as f:
        json.dump(out, f, indent=1)
    md = ["# 1. Building types (the places people live their lives in)", "",
          "Generated by `tools/places/make_places.py` with the same data as `godot_project/remake/characters/npc_places.json`. **%d place types**, %d building shells. Every job is an occupation in the generator (%s), and every role link is a role in `research/roles/roles.json` (%s)." % (
              len(T), len(SHELLS), "all valid" if not bad_jobs else "INVALID %s" % bad_jobs, "all valid" if not bad_roles else "INVALID %s" % bad_roles), "",
          "**A place's purpose is procedural.** A storefront becomes a grocery or a bar by its **signage and contents**, allocated per settlement from what the town needs (`tools/places/bake_places.py`); the catalog's current signage is only a hint. **Contents are categories**, the slots the models will be built to (fixtures, stock families, machinery), never particular models: those come after the game bible.", "",
          "## Shells", "", "| shell | what it is |", "|---|---|"]
    md += ["| `%s` | %s |" % (k, v) for k, v in SHELLS.items()]
    cats = []
    for t in T.values():
        if t["category"] not in cats:
            cats.append(t["category"])
    for c in cats:
        md += ["", "## " + c.capitalize(), "", "| type | shells | jobs | hours | visits (purpose, per person per week, dwell min) | contents: fixtures / stock / machinery | signage |", "|---|---|---|---|---|---|---|"]
        for k, t in T.items():
            if t["category"] != c:
                continue
            jobs = ", ".join("%s %d" % (o, n) for o, n in t["jobs"].items())
            vis = "; ".join("%s %.2g/wk %dm" % (v["purpose"], v["per_week"], v["dwell_min"]) for v in t["visits"])
            cont = " / ".join(", ".join(t["contents"][x]) or "–" for x in ("fixtures", "stock", "machinery"))
            md.append("| **%s** `%s`%s | %s | %s | %s–%s %s | %s | %s | %s |" % (
                t["name"], k, " (third place)" if t["third_place"] else "", ", ".join(t["shells"]), jobs or "–", t["hours"]["open"], t["hours"]["close"],
                t["hours"]["days"], vis or "–", cont, t["signage"]))
    os.makedirs(os.path.join(ROOT, "research", "lives"), exist_ok=True)
    with open(os.path.join(ROOT, "research", "lives", "01_building_types.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("%d types, %d shells; bad jobs %s; bad roles %s" % (len(T), len(SHELLS), bad_jobs or "none", bad_roles or "none"))


if __name__ == "__main__":
    main()
