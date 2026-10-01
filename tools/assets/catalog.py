"""The asset catalogue: every vehicle in research/lives/06_vehicles.md (npc_vehicles.json), how it is
built here and what Grok is asked to draw for it.

  family   existing  -- already modelled (the pod, the van, the aerostat, the bicycle)
           hull      -- a solid-bodied thing: a visual hull from the side and front (and top)
                        silhouettes, the reference images projected on as textures, wheels rigged
           transit   -- a hull with a hollow, furnished interior people ride in (tram, buses, train)
           frame     -- an open, wiry thing built part by part (bikes, chairs, carts)
  look     what it looks like, for Grok (the station's design language is added by brief.py)
  views    which reference views to ask for (side is always the master)
  plan     True when the plan (top) view matters to the shape (boats, wide machines)

Station design language (canon + the existing pod, van, aerostat and bicycle): friendly 1970s
retro-futurist industrial design; soft rounded corners; cream, chrome and muted colours; round lamps;
every vehicle electric or pedal (no grille, no exhaust, no fuel cap: a small charge-port flap).
"""

H, T, F, E = "hull", "transit", "frame", "existing"
SIDE, FRONT, REAR, TOP, Q34 = "side", "front", "rear", "top", "three_quarter"
HV = [SIDE, FRONT, REAR, Q34]          # the usual hull set
HVP = [SIDE, FRONT, REAR, TOP, Q34]     # with the plan view
ISEC, IPLAN, IAISLE = "interior_section", "interior_plan", "interior_aisle"
TVI = HV + [ISEC, IPLAN, IAISLE, "interior_layout"]         # transit: the hull set and the interior (cutaway, plan, down the aisle)
FV = [SIDE, FRONT, Q34]                 # frames: no projection, the side and front measure it

ASSETS = {
    # ---------------------------------------------------------------- existing
    "city_car": (E, "the pod (remake/blender/vehicles/groundcar.py)", []),
    "minivan": (E, "the van (remake/blender/vehicles/groundcar.py)", []),
    "personal_aerostat": (E, "the aerostat (remake/blender/vehicles/aerostat.py)", []),
    "bicycle": (E, "the bicycle (remake/blender/vehicles/bicycle.py)", []),
    # ---------------------------------------------------------------- household cars
    "sedan": (H, "a four-door family sedan with a gently rounded roof, wraparound glass, chrome bumpers and round headlamps, painted dusty sage green with a cream roof", HV),
    "station_wagon": (H, "a long, low station wagon with a squared-off rear hatch, roof rails, woodgrain side panels and chrome trim, painted cream", HV),
    "crossover_suv": (H, "a compact, tall crossover with a rounded nose, a two-tone body (muted terracotta below, cream above), black wheel arches and a roof rack", HV),
    "full_size_suv": (H, "a big boxy full-size SUV with three rows of windows, a tall upright nose, chrome trim and roof rails, painted deep navy", HV),
    "pickup_truck": (H, "a two-door pickup truck with a rounded cab, a long open cargo bed with a tailgate, chrome bumpers and round lamps, painted faded red with a white roof", HV),
    "sports_car": (H, "a low two-door sports coupe with a long sloping nose, a fastback roof and round pop-up-style lamps, painted mustard yellow with a black stripe", HV),
    "convertible": (H, "a two-door convertible with the soft top folded down, cream leather seats visible, chrome trim and whitewall tyres, painted pale sky blue", HV),
    "luxury_sedan": (H, "a long, stately luxury sedan with a formal upright roofline, lots of chrome trim and whitewall tyres, painted deep burgundy", HV),
    "taxi": (H, "a four-door sedan taxi painted chequer-free warm yellow with a cream roof sign box on top (blank, no letters)", HV),
    "company_car": (H, "a plain four-door sedan in light grey with a blank cream magnetic sign panel on the front door", HV),
    "unmarked_car": (H, "a plain dark charcoal four-door sedan with small hidden lights in the grille area and steel wheels", HV),
    "police_car": (H, "a four-door police patrol sedan in white with a broad navy-blue band along the sides, a low red-and-blue light bar on the roof, push bar on the front", HV),
    "police_suv": (H, "a police SUV in white with a navy-blue band along the sides and a roof light bar", HV),
    "fire_chief_car": (H, "a fire chief's SUV painted bright red with a white roof and a small roof light bar", HV),
    "hearse": (H, "a long black hearse with a raised rear compartment with curtained windows and chrome landau bars on the rear pillar", HV),
    "limousine": (H, "a long stretched white limousine with many side windows and chrome trim", HV),
    # ---------------------------------------------------------------- two wheels and small personal
    "motorcycle": (H, "an electric cruiser motorcycle with a teardrop tank-shaped battery cover, round headlamp, chrome forks, spoked wheels and a tan leather seat, painted cream and teal", HV),
    "scooter_moped": (H, "a small electric step-through moped scooter with curvy body panels, a round headlamp on the handlebars and a small rear carrier, painted mint green and cream", HV),
    "child_bicycle": (F, "a small child's bicycle with training wheels, a white wicker basket with a flower, streamers on the grips, painted cherry red with cream fenders", FV),
    "cargo_bike": (F, "a long Dutch-style front-loading cargo bicycle with a wooden box between the handlebars and the front wheel, a bench seat in the box, painted forest green", FV),
    "adult_tricycle": (F, "an adult upright tricycle with one front wheel, two rear wheels and a big wire basket between the rear wheels, painted lavender with cream fenders", FV),
    "kick_scooter": (F, "a child's kick scooter with a low deck, a tall T-handlebar with foam grips and small wheels, painted sky blue", FV),
    "skateboard": (F, "a wooden skateboard with a painted deck, four soft wheels and metal trucks", [SIDE, TOP, Q34]),
    "golf_cart": (F, "an electric two-seat golf cart / neighbourhood buggy with a cream canopy roof on four thin posts, a bench seat, small wheels and a rear basket, painted seafoam green", FV),
    "riding_mower": (H, "a small riding lawn mower / lawn tractor with a short hood, a single seat, a steering wheel and a mower deck underneath, painted Kelly green with cream wheels", HV),
    "motorhome": (H, "a large boxy 1970s motorhome with a rounded front, a cab-over bunk, wide picture windows and a stripe of orange, mustard and brown along a cream body", HV),
    "camper_trailer": (H, "a rounded teardrop-loaf travel trailer with polished aluminium sides, a cream stripe, round-cornered windows and a door on the side, on two wheels with a tow hitch", HV),
    "utility_trailer": (H, "a small open utility trailer with low mesh sides, two wheels with fenders and an A-frame tow hitch, painted dark grey", HV),
    "boat_trailer": (H, "a small fishing skiff sitting on a two-wheeled boat trailer with a winch post at the front", HV),
    # ---------------------------------------------------------------- mobility
    "manual_wheelchair": (F, "a lightweight manual wheelchair with large rear wheels with push rims, small front casters, a navy fabric seat and backrest and chrome frame", FV),
    "power_wheelchair": (F, "a power wheelchair with six small wheels, a padded grey seat with armrests, a joystick on the right arm and a battery base", FV),
    "mobility_scooter": (H, "a three-wheeled mobility scooter with a tiller handlebar, a basket on the front, a padded swivel seat and a rounded body, painted burgundy", HV),
    "rollator": (F, "a four-wheeled rollator walker with hand brakes, a padded seat between the handles and a fabric bag, chrome frame with blue accents", FV),
    "baby_stroller": (F, "a classic pram stroller with a deep cream fabric bassinet body, a folding navy hood, big spoked wheels and a chrome push handle", FV),
    "child_wagon": (F, "a classic red child's pull wagon with wooden slat sides, four wheels and a long pull handle", FV),
    # ---------------------------------------------------------------- carts
    "shopping_cart": (F, "a chrome wire shopping cart with a red plastic handle and a fold-down child seat", FV),
    "hand_truck": (F, "a two-wheeled hand truck dolly with a steel frame, a toe plate and pneumatic tyres, painted red", FV),
    "pallet_jack": (F, "a manual pallet jack with long forks, a pump handle on a steering wheel and small wheels, painted yellow", FV),
    "luggage_cart": (F, "a brass hotel luggage cart with an arched top bar, a carpeted platform and four wheels", FV),
    "housekeeping_cart": (F, "a hotel housekeeping cart with shelves of folded towels, a laundry bag hanging at one end and a trash bag at the other, beige panels", FV),
    "hospital_gurney": (F, "a hospital gurney stretcher with a white mattress, side rails, a raised backrest and four wheels on a chrome frame", FV),
    "food_cart": (F, "a street food cart with a stainless steel body, a striped red-and-cream umbrella, two big wheels and a push handle", FV),
    "wheelbarrow": (F, "a garden wheelbarrow with a green steel tray, wooden handles and one pneumatic front wheel", FV),
    # ---------------------------------------------------------------- public transport
    "school_bus": (T, "a classic school bus in warm school-bus yellow with black bumpers and rub rails, a stop arm, a rounded nose cab and a long row of windows", TVI),
    "transit_bus": (T, "a low-floor city transit bus with big windows, two doors on the right, a rounded front with a wide windscreen and a blank destination display, painted cream with a teal band", TVI),
    "tram": (T, "a long three-section articulated road tram on rubber tyres, with big rounded windscreen ends, wide windows, three double doors on the right side and a pantograph-free roof with smooth fairings, painted cream with a sea-teal band and chrome trim", TVI),
    "paratransit_van": (H, "a tall white van with a wheelchair lift at the side door, a blue stripe and rounded corners", HV),
    "hotel_shuttle": (H, "a small shuttle bus with a rounded front, big windows and a burgundy-and-cream livery", HV),
    "sightseeing_trolley": (T, "an open-sided sightseeing road trolley with a wooden-look body, brass rails, a curved roof and bench seats, painted dark green and gold", TVI),
    # ---------------------------------------------------------------- rail
    "passenger_train": (T, "an electric passenger train car with a rounded streamlined cab at one end, a row of large windows, two sliding doors on each side and a smooth roof, painted cream with a sea-teal stripe and chrome trim", TVI),
    "freight_locomotive": (H, "an electric freight locomotive with a full-width cab at each end, a smooth roof with fairings, two three-axle bogies, painted deep red with a cream stripe", HV),
    "boxcar": (H, "a railway boxcar with a sliding door in the middle of each side, ribbed steel sides and two bogies, painted oxide brown", HV),
    "covered_hopper": (H, "a covered grain hopper wagon with sloped hopper bays underneath, a ribbed rounded body and two bogies, painted light grey", HV),
    "tank_car": (H, "a railway tank car with a long cylindrical tank, a walkway on top and two bogies, painted black", HV),
    "flatcar": (H, "a railway flatcar with a long flat deck, stake pockets and two bogies, painted dark grey, empty", HV),
    "reefer_car": (H, "a refrigerated railway car with an insulated white body, a plug door and two bogies", HV),
    "hi_rail_truck": (H, "a track maintenance pickup truck with small extra rail wheels that fold down at front and rear, painted orange with a light bar", HV),
    # ---------------------------------------------------------------- commercial
    "delivery_van": (H, "a medium delivery van with a tall rounded body, sliding side door, rear double doors and blank cream side panels for a shop's name", HV),
    "parcel_van": (H, "a tall square step-van parcel delivery truck with a flat front, a sliding door at the driver's side and a brown body", HV),
    "mail_truck": (H, "a small, tall right-hand-drive mail delivery truck with a boxy body and a sliding door, white with a blue and red stripe", HV),
    "box_truck": (H, "a box truck with a rounded cab and a tall white box body with a roll-up rear door", HV),
    "refrigerated_truck": (H, "a refrigerated box truck with a white insulated box and a refrigeration unit above the cab", HV),
    "semi_truck": (H, "a cab-over semi tractor unit with a flat front, a sleeper cab and a fifth-wheel coupling, painted cream and teal, without a trailer", HV),
    "semi_trailer_dry": (H, "a long semi trailer with a box body painted deep mustard yellow with a cream stripe, rear doors, landing legs at the front and tandem axles at the back, without a tractor", HV),
    "semi_trailer_reefer": (H, "a long refrigerated semi trailer with an insulated body painted sky blue with a cream stripe and a refrigeration unit on the front face, without a tractor", HV),
    "milk_tanker": (H, "a milk tanker truck with a polished stainless steel tank and a rounded cab", HV),
    "grain_truck": (H, "a grain truck with a high-sided open box bed and a tarp roller, painted red", HV),
    "tow_truck": (H, "a tow truck with a rounded cab, a boom and wheel-lift at the back and amber beacons", HV),
    "service_van": (H, "a trades van with a ladder rack on the roof, toolboxes and a blank cream side panel", HV),
    "utility_bucket_truck": (H, "a utility truck with an aerial bucket lift folded on top and tool compartments, painted white", HV),
    "food_truck": (H, "a food truck with a serving hatch and awning on the side, a menu board area (blank) and a cheerful turquoise and cream paint scheme", HV),
    "ice_cream_truck": (H, "an ice-cream van with a sliding serving window, a pastel pink and cream body and a roof cone (no lettering)", HV),
    "armored_truck": (H, "an armoured cash truck with small thick windows, a heavy box body and steel plating, painted dark green", HV),
    # ---------------------------------------------------------------- farm
    "utility_tractor": (H, "a classic utility farm tractor with big rear wheels, small front wheels, an open seat with a rollover bar, a rounded hood, painted bright red with cream wheels", HV),
    "row_crop_tractor": (H, "a large row-crop tractor with an enclosed cab, huge dual rear wheels and a long hood, painted green with yellow wheels", HV),
    "combine_harvester": (H, "a combine harvester with a wide grain header at the front, a tall cab, a grain tank and a folded unloading auger, painted green", HVP),
    "grain_cart": (H, "a large farm grain cart with a big hopper body, a folded auger and two big tyres, painted red", HV),
    "hay_baler": (H, "a round hay baler with a rounded chamber and a pickup at the front, towed by a drawbar, painted green and yellow", HV),
    "hay_wagon": (H, "a flat wooden hay wagon with a rack at the front and back, four wheels and a drawbar, loaded with square hay bales", HV),
    "planter_drill": (H, "a farm seed planter with a long toolbar of row units and seed hoppers, folded for transport, painted green and yellow", HVP),
    "crop_sprayer": (H, "a self-propelled crop sprayer with tall thin wheels, a central tank, a cab and spray booms folded along its sides, painted white and green", HVP),
    "manure_spreader": (H, "a box manure spreader with beaters at the rear, two wheels and a drawbar, painted red", HV),
    "plough_disc": (H, "a disc harrow with two rows of round steel discs on a frame with transport wheels and a drawbar, painted red", HVP),
    "skid_steer": (H, "a compact skid-steer loader with a cage cab, lift arms either side and a bucket at the front, painted yellow", HV),
    "utv": (H, "a side-by-side utility vehicle with a roll cage, two seats, a small dump bed at the back and chunky tyres, painted olive green", HV),
    "atv": (H, "a four-wheeled ATV quad bike with handlebars, racks front and rear, and knobby tyres, painted red", HV),
    "livestock_trailer": (H, "a livestock trailer with slotted aluminium sides, a rear gate and tandem wheels", HV),
    "farm_pickup_flatbed": (H, "a farm flatbed truck with a stake-side wooden flat bed and a rounded cab, painted green", HV),
    # ---------------------------------------------------------------- industry
    "forklift": (H, "a forklift truck with an overhead guard, a mast with forks at the front and a counterweight at the back, painted yellow", HV),
    "dump_truck": (H, "a dump truck with a steel tipping body and a rounded cab, painted orange", HV),
    "cement_mixer": (H, "a concrete mixer truck with a big rotating drum and chute, painted white and orange", HV),
    "backhoe_loader": (H, "a backhoe loader with a front bucket, a cab and a digging arm folded at the back, painted yellow", HV),
    "excavator": (H, "a tracked excavator with a cab, an engine housing and a long boom and arm with a bucket, painted yellow", HV),
    "mobile_crane": (H, "a mobile crane truck with a long folded telescopic boom, outriggers and a cab, painted yellow", HV),
    "low_loader": (H, "a low-loader semi trailer with a dropped deck and ramps at the back, painted blue, empty, without a tractor", HV),
    "travel_lift": (F, "a boat travel lift: a tall steel portal gantry on four wheeled legs with lifting slings between them, painted blue", FV),
    "yard_tug": (H, "a yard tractor (terminal tug) with a one-person offset cab and a fifth wheel, painted yellow", HV),
    # ---------------------------------------------------------------- emergency
    "fire_engine": (H, "a fire engine pumper with a flat-front crew cab, roll-up lockers, hose beds and a light bar, painted bright red with white trim", HV),
    "ladder_truck": (H, "an aerial ladder fire truck with a long ladder lying along the top, painted red with white trim", HV),
    "brush_truck": (H, "a brush fire and rescue truck on a pickup chassis with a utility body and a water tank, painted red", HV),
    "ambulance": (H, "an ambulance with a box body, a white and red livery with a blank panel where a symbol would be, and light bars", HV),
    "coast_guard_boat": (H, "a coast guard patrol boat with a cabin and radar mast, a white hull with a red stripe", HVP),
    "lifeguard_truck": (H, "a beach lifeguard pickup truck with a rescue board on a rack, painted yellow", HV),
    "rescue_board": (F, "a long red lifeguard rescue paddleboard with handles along its rails", [SIDE, TOP, Q34]),
    # ---------------------------------------------------------------- civic
    "garbage_truck": (H, "a rear-loading refuse truck with a compactor body and a rounded cab, painted green and white", HV),
    "recycling_truck": (H, "a side-loading recycling truck with an automated arm, painted blue and white", HV),
    "street_sweeper": (H, "a compact street sweeper with round side brushes and a hopper, painted white", HV),
    "public_works_pickup": (H, "a public works pickup truck with an amber beacon and a toolbox, painted white with an orange stripe", HV),
    "parks_mower": (H, "a zero-turn ride-on park mower with a wide deck and a seat with a roll bar, painted orange", HV),
    # ---------------------------------------------------------------- water
    "lobster_boat": (H, "a wooden-style inshore lobster boat with a high bow, a small forward wheelhouse and a low open work deck aft, white hull with a red waterline", HVP),
    "trawler": (H, "a stern trawler fishing boat with a tall wheelhouse, gantry and net drum at the stern, a blue hull and white superstructure", HVP),
    "fishing_skiff": (H, "a small aluminium fishing skiff with a tiller electric outboard motor", HVP),
    "rowboat_dinghy": (H, "a wooden rowboat with two bench seats and oars resting in the oarlocks, varnished with a white stripe", HVP),
    "canoe_kayak": (H, "a red canvas-and-wood canoe with thwarts and a cane seat", HVP),
    "sailboat": (H, "a 9-metre sloop sailboat with a white hull, a small cabin and a tall mast with a furled mainsail", HVP),
    "pontoon_boat": (H, "a pontoon boat with two aluminium tubes, a fenced deck with lounge seats and a bimini top", HVP),
    "cabin_cruiser": (H, "a 1970s cabin cruiser motor yacht with a flybridge, a white hull and teak trim", HVP),
    "personal_watercraft": (H, "a sit-down personal watercraft (jet ski) with handlebars, painted white and teal", HVP),
    "ferry": (H, "a passenger and car ferry with a white superstructure, two decks of windows, a dark blue hull and a ramp at the bow", HVP),
    "workboat_tug": (H, "a harbour tug with a tall wheelhouse, heavy rubber fenders around the hull, a red hull and black funnel-shaped mast", HVP),
    "barge": (H, "a flat deck cargo barge with a low hull, rails and bollards, painted dark red", HVP),
    "pedal_boat": (H, "a swan-shaped pedal boat with a white swan neck at the front and two seats", HVP),
    # ---------------------------------------------------------------- amusement
    "go_kart": (F, "a go-kart with a low tubular frame, a moulded seat, a small steering wheel and bumpers, painted red", FV),
    "bumper_car": (H, "a fairground bumper car with a rubber bumper ring, a single seat, a pole at the back and glossy cherry-red bodywork", HV),
    "kiddie_train": (H, "a small amusement-park train: a stubby locomotive with a round boiler-shaped front and two open passenger cars, painted red and gold", HV),
    "surrey_bike": (F, "a four-wheel surrey pedal cart with two bench seats side by side, a fringed canopy roof, painted cream with red", FV),
    # ---------------------------------------------------------------- station
    "cargo_aerostat": (H, "a heavy-lift cargo airship: a large rounded envelope, ducted fans on side pylons, and a cargo sling frame under a small gondola, cream with teal bands", HVP),
    "rescue_aerostat": (H, "a small medical rescue airship with a rounded white envelope, red stripes, a glazed gondola and ducted fans", HVP),
    "tram_maintenance_car": (H, "a road tram maintenance truck with a work platform on the roof and amber beacons, painted orange and cream", HV),
    "spoke_elevator_car": (H, "a large cylindrical elevator car with a ring of windows, a domed roof and sliding doors, cream and chrome", [SIDE, TOP, Q34]),
    "passenger_shuttle": (H, "a retro-futurist passenger spaceplane shuttle with stubby wings, a rounded nose and a row of windows, cream and teal", HVP),
    "supply_freighter": (H, "a boxy cargo spacecraft with stacked container modules, a forward command module and a drive section, grey and cream", HVP),
    "cargo_mule": (H, "a small boxy space tug with manipulator arms and thruster pods, white and orange", HV),
    "eva_sled": (H, "a one-person open maintenance pod with a seat, handholds, a robot arm and thrusters, white and orange", HV),
    "utility_cart": (H, "a small electric utility cart with a two-seat cab, a flat bed and a canopy, painted cream with a teal stripe", HV),
    "hydroponics_harvest_cart": (F, "a tall wheeled harvest cart with three shelves of plastic crates, stainless steel frame", FV),
}
