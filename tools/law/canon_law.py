"""Columbia's laws of the street: the state baselines, the six large cities' ordinances (parking,
sidewalks, streets, transit stop signs, subdivisions, zoning), the settlements each governs, the
sign catalogue, the building code tokens and the design rules drawn from the planning literature.
The user (2026-10-01): "Each large city will have its own unique variation of Public Transit signs
and parking ordinances. All signs will follow the USA standard. The smaller cities, towns and
settlements will follow the signs and ordinances of the nearest large city ... All of these rules
will later be compiled into in-game lawbooks and a legal system."

make_law.py validates this and writes godot_project/remake/law/*.json (the engine's) and
research/law/*.md (to read).

Sources and their weight (research/law/README.md):
  - Ohio Revised Code, fetched 2026-10-01 from codes.ohio.gov: 4511.21 (speeds), 4511.68 (where
    parking is prohibited), 4511.69 (how to park), 711.05 / 711.10 (plats, subdivision rules), 729.01
    (sidewalks, curbs and gutters: the abutting owner's), 3781.01 (local building rules may add to the
    state code where they don't conflict). Quoted closely: these are the station's state law.
  - The MUTCD (FHWA, Part 2B fetched 2026-10-01): sign codes and families.
  - The cities' own codified ordinances (Cleveland, Columbus, Cincinnati, Dayton, Toledo, Fort Wayne)
    could not be fetched -- the code libraries (Municode, American Legal) refuse automated readers
    and the session's web search ran out -- so each city's variant here is THE STATION'S OWN LAW,
    modelled on what that city is known for and on common Ohio / Indiana municipal practice. Every
    such rule says so (basis: "station"); nothing here claims to quote a real city ordinance.
  - Indiana baselines (the Fort Wayne-modelled city) are from general knowledge of the Indiana
    Code (IC 9-21-5, IC 9-21-16, IC 36-7-4-700), not fetched; marked basis: "knowledge".
Units: the station is metric (SSC road standard); feet are kept beside metres where the law speaks
in feet.
"""

FT = 0.3048


def ft(x):
    return round(x * FT, 2)


# ------------------------------------------------------------------ the state baselines
STATE = {
    "ohio": {
        "name": "the Ohio Revised Code (as carried aboard: the Charter's Code of the Road, art. 30)",
        "speed": {"school_zone_mph": 20, "business_district_mph": 25, "urban_district_mph": 25, "alley_mph": 15,
                  "state_route_in_town_mph": 35, "source": "ORC 4511.21", "basis": "fetched"},
        "no_parking": [   # ORC 4511.68 (A): where no one may stand or park
            ("sidewalk", None), ("in_front_of_driveway", None), ("within_intersection", None),
            ("from_hydrant", ft(10)), ("on_crosswalk", None), ("from_crosswalk_at_intersection", ft(20)),
            ("before_stop_yield_or_signal", ft(30)), ("opposite_safety_zone_ends", ft(30)), ("from_rail_crossing", ft(50)),
            ("from_fire_station_driveway", ft(20)), ("opposite_fire_station", ft(75)), ("beside_excavation", None),
            ("double_parking", None), ("bridge_or_tunnel", None), ("where_signed", None), ("from_parked_vehicle", ft(1)),
            ("freeway_roadway", None), ("bicycle_lane", None)],
        "no_parking_source": "ORC 4511.68 (fetched)",
        "parking_position": {"max_from_curb_m": ft(1), "side": "right, with the flow", "one_way_left_by_ordinance": True,
                             "angle_by_ordinance_only": True, "angle_min_clear_roadway_m": ft(25),
                             "disability_extra_hours": 2, "disability_fine_usd": [250, 500], "source": "ORC 4511.69 (fetched)"},
        "sidewalks": {"duty": "the abutting owner builds and repairs sidewalks, curbs and gutters; the city may order it and, if not done, do it and assess the cost on the lot",
                      "source": "ORC 729.01 (fetched)"},
        "subdivision": {"approval_outside_towns": "the county commissioners (here: the Regional Planning Board of the governing city)",
                        "decision_days": 30, "deemed_approved_if_late": True, "min_lot_sqft_floor": 4800, "appeal_days": 60,
                        "rules_may_cover": ["street arrangement and coordination", "open spaces for traffic, utilities, fire access, recreation, light and air",
                                            "avoiding congestion", "health board review", "sewage rules"],
                        "source": "ORC 711.05, 711.10 (fetched)"},
        "building": {"state_code": "the Ohio Building Code (OAC 4101:1; the International Building Code as amended)",
                     "residential_code": "the Residential Code of Ohio (OAC 4101:8; the International Residential Code as amended)",
                     "local_additions": "a city may add regulations that don't conflict; the Board of Building Standards may void a conflicting one not needed for health or safety (ORC 3781.01, fetched)"},
    },
    "indiana": {
        "name": "the Indiana Code (as carried aboard: the Oceanview Compact's Indiana charter, a founders' inheritance)",
        "speed": {"urban_district_mph": 30, "alley_mph": 15, "school_zone_mph": 20, "source": "IC 9-21-5-2 (knowledge)", "basis": "knowledge"},
        "no_parking": [("sidewalk", None), ("in_front_of_driveway", None), ("within_intersection", None), ("from_hydrant", ft(15)),
                       ("on_crosswalk", None), ("from_crosswalk_at_intersection", ft(20)), ("before_stop_yield_or_signal", ft(30)),
                       ("from_rail_crossing", ft(50)), ("from_fire_station_driveway", ft(20)), ("opposite_fire_station", ft(75)),
                       ("double_parking", None), ("bridge_or_tunnel", None), ("where_signed", None)],
        "no_parking_source": "IC 9-21-16-5 (knowledge)",
        "parking_position": {"max_from_curb_m": ft(1), "side": "right, with the flow", "source": "IC 9-21-16-3 (knowledge)"},
        "sidewalks": {"duty": "the abutting owner keeps the sidewalk; the city may build and assess (IC 36-9 (knowledge))"},
        "subdivision": {"approval": "the plan commission under the subdivision control ordinance (IC 36-7-4-700, knowledge)"},
        "building": {"state_code": "the Indiana Building Code (675 IAC 13; the IBC as amended)", "residential_code": "the Indiana Residential Code (675 IAC 14; the IRC as amended)"},
    },
}

# ------------------------------------------------------------------ the signs (USA standard: MUTCD codes)
SIGNS = [
    # code, name, legend, colours, use
    ("R1-1", "STOP", "STOP", "white on red octagon", "minor street at a junction"),
    ("R2-1", "SPEED LIMIT", "SPEED LIMIT nn", "black on white", "speed limits (km/h aboard, the legend in the station's metric)"),
    ("R7-1", "NO PARKING ANY TIME", "NO PARKING ANY TIME with arrow", "red on white", "no-parking stretches"),
    ("R7-2", "NO PARKING (times)", "NO PARKING 8 AM - 5 PM with arrow", "red on white", "timed no-parking (sweeping, rush hours)"),
    ("R7-108", "TIMED PARKING", "2 HOUR PARKING 8 AM - 6 PM with arrow", "green on white", "time-limited parking"),
    ("R7-20", "PAY STATION", "PAY STATION with arrow", "green on white", "metered blocks"),
    ("R7-8", "RESERVED PARKING (accessible)", "symbol of accessibility, RESERVED PARKING", "green/blue on white", "accessible spaces (ORC 4511.69)"),
    ("R7-107", "NO PARKING BUS/TRAM STOP", "NO PARKING + transit symbol", "red on white", "the kerb at a tram stop (the station uses the tram symbol)"),
    ("R7-201P", "TOW-AWAY ZONE", "TOW-AWAY ZONE plaque", "red on white", "with a no-parking sign"),
    ("R7-202P", "THIS SIDE OF SIGN", "THIS SIDE OF SIGN plaque", "black on white", "with a parking sign"),
    ("R7-203", "EMERGENCY ROUTE", "EMERGENCY SNOW ROUTE (aboard: EMERGENCY ROUTE / FLOOD ROUTE)", "white on red and black on white", "routes cleared in an emergency (no snow since VY 212: flood and evacuation routes)"),
    ("R8-3", "NO PARKING (symbol)", "P with red circle and slash", "red/black on white", "no parking where a word sign won't fit"),
    ("R8-3hP", "times plaque", "8 AM - 6 PM", "black on white", "under R8-3"),
    ("D3-1", "STREET NAME", "street name", "white on green", "every junction (subdivision rules)"),
    ("D4-2", "PARK & RIDE", "PARK & RIDE with transit symbol", "white on green", "the way to a park-and-ride lot"),
    ("D9-11", "PARKING (guide)", "P", "white on blue", "the way to a public lot"),
    ("W14-1", "DEAD END", "DEAD END", "black on yellow", "a street with no way through"),
    ("W14-2", "NO OUTLET", "NO OUTLET", "black on yellow", "the mouth of a cul-de-sac or loop with one way out"),
    ("S1-1", "SCHOOL", "school children symbol", "black on fluorescent yellow-green", "school zones"),
    ("R10-? / agency", "TRAM STOP (city design)", "the city transit authority's own stop flag (not a MUTCD regulatory sign: stop flags are the agency's)", "per city", "every tram stop"),
]

# ------------------------------------------------------------------ the six large cities
#   Each a variant of its basis city, the station's own law (see the module docstring).
CITIES = [
    dict(id="port_carrow", name="Port Carrow", basis_city="Cleveland, Ohio", state="ohio", code="Port Carrow Codified Ordinances (PCCO)",
         character="the harbour capital of the North Shore: dense grid, lake winds, a downtown of brick blocks",
         transit=dict(authority="Port Carrow Lakeshore Transit (PCLT)", stop_flag="navy rectangle, white tram symbol in a white ring, a bronze stripe at the foot; route numbers in white boxes",
                      colours=["#1d2b4f", "#ffffff", "#9a6b34"], shape="rectangle 450 x 600 mm on its own post"),
         parking=dict(
             downtown=dict(meters=True, hours="8 AM - 6 PM Mon-Sat", limit_h=2, pay="pay stations by the block", sign="R7-108 + R7-20"),
             residential=dict(both_sides_min_m=ft(30), one_side_min_m=ft(24), none_below_m=ft(24), overnight=True, max_hours=48,
                              sweeping="one weekday morning a month, R7-2 'NO PARKING 8 AM - 11 AM 2ND TUE'"),
             special=["Emergency Routes (R7-203): no parking when the Marshals declare an emergency; tow-away",
                      "Harbour loading zones 6 AM - 10 AM on the dock streets",
                      "Regatta Week: the Lakeshore Road kerbs closed (temporary R7-1 hoods)"],
             angle_parking=False, permit_zones=["Côte quarter residential permit (R7-108 'EXCEPT BY PERMIT')"], code_section="PCCO 451"),
         sidewalks=dict(core_min_m=ft(12), residential_walk_m=ft(5), tree_lawn_m=ft(6), required="both sides of every street in the city; on one side at least of county roads within the limits",
                        snow="(no snow aboard) the owner clears leaves and storm debris within 24 h", code_section="PCCO 511"),
         streets=dict(local_curb_to_curb_m=ft(30), local_row_m=ft(50), collector_curb_to_curb_m=ft(36), main_curb_to_curb_m=ft(40)),
         speed=dict(residential_kmh=40, business_kmh=40, school_kmh=30, alley_kmh=25)),
    dict(id="kessler", name="Kessler", basis_city="Columbus, Ohio", state="ohio", code="Kessler City Code (KCC)",
         character="the capital: the Assembly Hall district, government offices, a planned grid",
         transit=dict(authority="Capital Area Tramways (CAT)", stop_flag="red roundel on a white disc, a white tram symbol on the bar, the stop name below in a white panel",
                      colours=["#b31b1b", "#ffffff", "#222222"], shape="round 600 mm disc over a 300 x 450 mm name panel"),
         parking=dict(
             downtown=dict(meters=True, hours="8 AM - 10 PM Mon-Sat", limit_h=3, pay="pay stations; the Assembly District 1-hour on session days", sign="R7-108 + R7-20"),
             residential=dict(both_sides_min_m=ft(28), one_side_min_m=ft(22), none_below_m=ft(22), overnight=True, max_hours=72,
                              sweeping="none (the city sweeps by schedule, signed street by street)"),
             special=["the 72-hour rule: no vehicle may stay on a public street longer than 72 hours (the station's rule, after Columbus's practice)",
                      "Assembly District permit parking for residents (R7-108 'EXCEPT BY PERMIT')",
                      "Charter Day: the parade route closed from 6 AM (temporary R7-1)"],
             angle_parking=False, permit_zones=["Assembly District", "Old Kessler"], code_section="KCC 2105"),
         sidewalks=dict(core_min_m=ft(14), residential_walk_m=ft(5), tree_lawn_m=ft(5), required="both sides of every street; new subdivisions build them with the street (Complete Streets policy)",
                        code_section="KCC 4123"),
         streets=dict(local_curb_to_curb_m=ft(28), local_row_m=ft(50), collector_curb_to_curb_m=ft(36), main_curb_to_curb_m=ft(44)),
         speed=dict(residential_kmh=40, business_kmh=40, school_kmh=30, alley_kmh=25)),
    dict(id="solana_point", name="Solana Point", basis_city="Cincinnati, Ohio", state="ohio", code="Solana Point Municipal Code (SPMC)",
         character="the South Shore's boom city: hills down to the sea, stairs between streets, crowded kerbs",
         transit=dict(authority="Solana Metro Tranvía (SMT)", stop_flag="sun-yellow pennant shape, black tram symbol, the stop name in Spanish and English",
                      colours=["#ecb928", "#111111", "#1e8080"], shape="pennant 450 x 650 mm"),
         parking=dict(
             downtown=dict(meters=True, hours="9 AM - 9 PM Mon-Sat, 1 PM - 9 PM Sun on Pier Plaza", limit_h=2, pay="pay stations", sign="R7-108 + R7-20"),
             residential=dict(both_sides_min_m=ft(32), one_side_min_m=ft(26), none_below_m=ft(26), overnight=True, max_hours=48,
                              sweeping="none; on hill streets narrower than 26 ft, parking on the downhill side only"),
             special=["Rush-hour arterials: NO PARKING 7 - 9 AM / 4 - 6 PM toward downtown (R7-2 + R7-201P TOW-AWAY ZONE)",
                      "Hill streets: wheels turned to the kerb on grades over 5 %",
                      "Suns game days: the Sun Bowl streets by permit"],
             angle_parking=False, permit_zones=["Pier Plaza residents", "the Sun Bowl blocks on game days"], code_section="SPMC 507"),
         sidewalks=dict(core_min_m=ft(12), residential_walk_m=ft(5), tree_lawn_m=ft(4), required="both sides; public stairs where streets are too steep to join (steps 7 in max, handrails both sides)",
                        code_section="SPMC 721"),
         streets=dict(local_curb_to_curb_m=ft(26), local_row_m=ft(40), collector_curb_to_curb_m=ft(34), main_curb_to_curb_m=ft(40)),
         speed=dict(residential_kmh=40, business_kmh=40, school_kmh=30, alley_kmh=25)),
    dict(id="harrow_falls", name="Harrow Falls", basis_city="Dayton, Ohio", state="ohio", code="Harrow Falls Revised Code of General Ordinances (HFRCGO)",
         character="the mill town at the Falls: the Works, the river, workers' terraces, the bluff",
         transit=dict(authority="Kettle Valley Transit (KVT)", stop_flag="green shield (the old mill-town crest), white tram symbol, a white band with the stop name",
                      colours=["#2f6b3a", "#ffffff", "#7a2c1e"], shape="shield 500 x 650 mm"),
         parking=dict(
             downtown=dict(meters=True, hours="8 AM - 6 PM Mon-Fri", limit_h=2, pay="coin and card meters on posts", sign="R7-108"),
             residential=dict(both_sides_min_m=ft(36), one_side_min_m=ft(28), none_below_m=ft(28), overnight=True, max_hours=72,
                              sweeping="none"),
             special=["Flood Routes (R7-203, aboard: FLOOD ROUTE): no parking when the Kettle runs high; tow-away (after the Kettle Flood, VY 447)",
                      "Works shift change: the Falls Yard streets NO PARKING 5:30 - 7 AM and 2:30 - 4 PM",
                      "Trucks over 4.5 t: not on residential streets overnight"],
             angle_parking=True, permit_zones=[], code_section="HFRCGO 76"),
         sidewalks=dict(core_min_m=ft(10), residential_walk_m=ft(4), tree_lawn_m=ft(4), required="both sides in the city; one side on the bluff roads",
                        code_section="HFRCGO 92"),
         streets=dict(local_curb_to_curb_m=ft(30), local_row_m=ft(50), collector_curb_to_curb_m=ft(36), main_curb_to_curb_m=ft(48)),
         speed=dict(residential_kmh=40, business_kmh=40, school_kmh=30, alley_kmh=25)),
    dict(id="brightwater", name="Brightwater", basis_city="Toledo, Ohio", state="ohio", code="Brightwater Municipal Code (BMC)",
         character="the pleasure town of the North Shore: the boardwalk, the arcades, summer crowds",
         transit=dict(authority="Brightwater Boardwalk Trams (BBT)", stop_flag="teal lollipop disc with a cream rim, white tram symbol, the stop name on a cream bar",
                      colours=["#1f8a8a", "#f2e6c8", "#c0392b"], shape="disc 550 mm over a bar 600 x 150 mm"),
         parking=dict(
             downtown=dict(meters=True, hours="10 AM - 10 PM, Memorial Day to Labor Day (the summer season)", limit_h=3, pay="seasonal pay stations", sign="R7-108 + R7-20 + season plaque"),
             residential=dict(both_sides_min_m=ft(30), one_side_min_m=ft(24), none_below_m=ft(24), overnight=True, max_hours=48,
                              sweeping="none"),
             special=["Angle parking on the Boardwalk approaches (back-in angle, 45 degrees)",
                      "Summer-season beach permit lots",
                      "Emergency Routes (R7-203) on the Coast Highway"],
             angle_parking=True, permit_zones=["Beach blocks (summer)"], code_section="BMC 335"),
         sidewalks=dict(core_min_m=ft(12), residential_walk_m=ft(5), tree_lawn_m=ft(4), required="both sides; the Boardwalk counts as the sidewalk of the streets that end at it",
                        code_section="BMC 521"),
         streets=dict(local_curb_to_curb_m=ft(30), local_row_m=ft(50), collector_curb_to_curb_m=ft(36), main_curb_to_curb_m=ft(44)),
         speed=dict(residential_kmh=40, business_kmh=30, school_kmh=30, alley_kmh=25)),
    dict(id="oceanview", name="Oceanview", basis_city="Fort Wayne, Indiana", state="indiana", code="Oceanview Code of Ordinances (OCO)",
         character="the resort city of the South Shore, settled by Indiana families who kept their own code",
         transit=dict(authority="Oceanview Citilink Trams (OCT)", stop_flag="orange square, white tram symbol, a white route strip; the stop name on a blue plate",
                      colours=["#e2711d", "#ffffff", "#1f4e8c"], shape="square 500 mm over a plate 500 x 150 mm"),
         parking=dict(
             downtown=dict(meters=True, hours="9 AM - 6 PM Mon-Fri", limit_h=2, pay="pay stations", sign="R7-108 + R7-20"),
             residential=dict(both_sides_min_m=ft(30), one_side_min_m=ft(22), none_below_m=ft(22), overnight=True, max_hours=48,
                              sweeping="none"),
             special=["No parking 2 - 6 AM on the Ocean Road strip (R7-2)", "Emergency Routes (R7-203)"],
             angle_parking=False, permit_zones=[], code_section="OCO 72"),
         sidewalks=dict(core_min_m=ft(10), residential_walk_m=ft(5), tree_lawn_m=ft(5), required="both sides; plan commission may waive one side on rural-edge streets",
                        code_section="OCO 97"),
         streets=dict(local_curb_to_curb_m=ft(28), local_row_m=ft(50), collector_curb_to_curb_m=ft(36), main_curb_to_curb_m=ft(44)),
         speed=dict(residential_kmh=50, business_kmh=50, school_kmh=30, alley_kmh=25)),
]

# ------------------------------------------------------------------ who follows whom
#   (settlement id, governing large city, why: proximity and economic ties)
GOVERNED = [
    ("bellhaven", "harrow_falls", "3.9 km; the Kettle Valley tram; the College's printing and the Works' apprentices"),
    ("cedar_ford", "harrow_falls", "the Kettle Valley; flood routes shared since the Kettle Flood"),
    ("dunmore_crossing", "harrow_falls", "2.6 km; the Ring Line depot; Elias Thornbury's town"),
    ("port_tamsin", "harrow_falls", "2.6 km; Lake Tamsin's trade runs through the Falls"),
    ("victory_bay", "harrow_falls", "1.7 km; the lake island's ferry lands below the Falls"),
    ("fenwick", "port_carrow", "2.6 km; the clockmakers sell through Port Carrow's merchants"),
    ("marlowe", "port_carrow", "2.6 km; Northland grain to the harbour"),
    ("tern_harbor", "port_carrow", "the North Shore fishing fleet lands its catch at Port Carrow"),
    ("haskins_corner", "brightwater", "2.3 km; the crossroads store supplies the boardwalk"),
    ("loomis_grove", "brightwater", "1.5 km; the orchards' fruit stands on the boardwalk"),
    ("haven_point", "brightwater", "the North Shore coast road; the summer trade"),
    ("pelican_cove", "solana_point", "the canneries; Solana Point's market"),
    ("playa_verde", "solana_point", "founded by Solana Point families; Lake Spanish"),
    ("pruett", "kessler", "the Southland farms supply the capital"),
    ("calder", "kessler", "the southland's hospital town, a half-hour down US 30 from the capital; its courts and registry are Kessler's"),
    ("tamarack", "oceanview", "2.1 km; the dairy's milk to the resort hotels"),
]
TIERS = [("city", 20000), ("town", 10000), ("village", 4000), ("hamlet", 0)]
FAST_TRAVEL_TIERS = ("city", "town")          # the largest two tiers (the user's)

# ------------------------------------------------------------------ tram stop zones (every city: the station's own rule)
#   US cities sign a bus stop zone of 80-150 ft of kerb (longer for articulated buses; TCRP Report 19,
#   knowledge). A Carrow tram runs to four sections (~38 m), and trams stop on both kerbs of a street
#   (each running on its right), so the station takes the long end on both kerbs.
TRAM_STOP_ZONE = {"half_length_m": ft(150), "both_kerbs": True,
                  "sign": "R7-107 NO PARKING (tram symbol) at both ends of the zone, arrows pointing into it",
                  "paint": "no parking lane line through the zone", "basis": "the station's own rule (TCRP Report 19 bus zones, knowledge)"}

# ------------------------------------------------------------------ subdivisions (each city's Regional Planning Board)
SUBDIVISION = {
    "_about": "Subdivision rules the station's Regional Planning Boards apply (ORC 711.10 lets the board make them; Indiana's plan commissions likewise). Values are the station's, in the range Ohio and Indiana county regulations use (from knowledge; the county regulations themselves were not fetched). Each city may override a value (CITY_SUBDIVISION).",
    "local_street": {"row_m": ft(50), "pavement_back_to_back_m": ft(28), "parking": "one side", "sidewalks": "both sides, 5 ft, 4 ft tree lawn",
                     "curb_radius_m": ft(25), "speed_kmh": 40},
    "collector": {"row_m": ft(60), "pavement_back_to_back_m": ft(36), "parking": "both sides or none", "sidewalks": "both sides, 5 ft"},
    "cul_de_sac": {"max_length_m": ft(600), "max_lots": 20, "turnaround_pavement_radius_m": ft(40), "turnaround_row_radius_m": ft(50),
                   "sign": "W14-2 NO OUTLET at its mouth"},
    "loop_street": {"max_length_m": ft(2400), "sign": "W14-2 NO OUTLET where its only way out is one entrance"},
    "blocks": {"max_length_m": ft(1320), "min_length_m": ft(400), "mid_block_walk_when_longer_than_m": ft(900)},
    "intersections": {"min_angle_deg": 75, "min_offset_m": ft(125), "max_legs": 4, "stop_control": "STOP (R1-1) on the subdivision street where it meets a collector or arterial; no all-way stops in the subdivision"},
    "access": {"min_entrances_over_lots": [[30, 2]], "stub_to_adjoining_land": True},
    "lots": {"min_frontage_m": ft(60), "min_area_m2": round(4800 * FT * FT), "corner_lot_extra_width_m": ft(10)},
    "signs": {"street_name": "D3-1 at every intersection, both streets", "speed_limit": "R2-1 at each entrance (40 km/h = 25 mph)",
              "no_outlet": "W14-2 at a cul-de-sac's or one-entrance loop's mouth", "stop": "R1-1 on the minor leg", "school": "S1-1 where a school fronts"},
    "required_improvements": ["paved streets with curb and gutter", "sidewalks both sides", "street trees every 40 ft in the tree lawn",
                              "street lights at intersections and every 200 ft", "storm sewers", "monuments at block corners"],
}

# ------------------------------------------------------------------ zoning and the building code (tokens for the generator)
ZONING = {
    "_about": "Zoning districts (each city's zoning code; the station's values, in the range the basis cities use, from knowledge). Setbacks in metres; heights in metres; parking per unit / per 100 m2.",
    "districts": {
        "R-1": {"use": "single-family", "min_lot_m2": 650, "min_frontage_m": ft(60), "front_m": ft(25), "side_m": ft(6), "rear_m": ft(30), "max_height_m": ft(35), "max_coverage": 0.35, "parking": {"per_unit": 2}},
        "R-2": {"use": "one- and two-family", "min_lot_m2": 465, "min_frontage_m": ft(50), "front_m": ft(20), "side_m": ft(5), "rear_m": ft(25), "max_height_m": ft(35), "max_coverage": 0.40, "parking": {"per_unit": 2}},
        "R-3": {"use": "townhouses and small apartments", "min_lot_m2": 280, "min_frontage_m": ft(25), "front_m": ft(15), "side_m": ft(0), "rear_m": ft(20), "max_height_m": ft(45), "max_coverage": 0.55, "parking": {"per_unit": 1.5}},
        "C-1": {"use": "neighbourhood commercial", "front_m": ft(0), "front_max_m": ft(10), "side_m": ft(0), "rear_m": ft(15), "max_height_m": ft(45), "max_coverage": 0.8, "parking": {"per_100m2": 2.7}},
        "C-2": {"use": "downtown core (form-based: build to the back of the sidewalk)", "front_m": 0.0, "front_max_m": 0.0, "side_m": 0.0, "rear_m": ft(10), "max_height_m": ft(85), "max_coverage": 1.0, "parking": {"per_100m2": 0.0, "note": "none required downtown; public lots and garages serve it"}},
        "M-1": {"use": "light industry, the Works", "front_m": ft(30), "side_m": ft(15), "rear_m": ft(20), "max_height_m": ft(60), "max_coverage": 0.6, "parking": {"per_100m2": 1.0}},
        "P": {"use": "parks, schools, civic", "front_m": ft(30), "side_m": ft(20), "rear_m": ft(20), "max_height_m": ft(45)},
        "A": {"use": "agriculture", "min_lot_m2": 20000, "front_m": ft(50), "side_m": ft(25), "rear_m": ft(50), "max_height_m": ft(35)},
    },
    "building_kind_district": {"house": "R-1", "cottage": "R-2", "bungalow": "R-2", "singlehouse": "R-1", "shingle": "R-2", "beachhouse": "R-2",
                               "condo": "R-3", "store": "C-2", "hotel": "C-2", "motel": "C-1", "civic": "P", "church": "P", "school": "P",
                               "industrial": "M-1", "farm": "A"},
}

BUILDING_CODE = {
    "_about": "Tokens from the state building codes for the procedural generator: the Ohio Building Code (OAC 4101:1, the IBC as amended) and the Residential Code of Ohio (OAC 4101:8, the IRC as amended), and Indiana's (675 IAC 13 / 14). The adoption is fetched (ORC 3781.01, OAC rule pages); the numeric provisions are the model codes' as widely published (from knowledge -- the ICC texts are copyrighted and were not fetched). Each value names its section.",
    "occupancy_groups": {"A": "assembly (theatres, churches, restaurants over 50)", "B": "business (offices, clinics)", "E": "educational (schools)",
                         "F": "factory", "H": "high hazard", "I": "institutional (hospitals, care)", "M": "mercantile (stores)",
                         "R-1": "transient (hotels, motels)", "R-2": "apartments (3+ units)", "R-3": "one- and two-family (outside the residential code)",
                         "S": "storage", "U": "utility (garages, sheds)"},
    "construction_types": {"I-A": "non-combustible, 3 h frame", "I-B": "non-combustible, 2 h", "II-A": "non-combustible, 1 h", "II-B": "non-combustible, unprotected",
                           "III-A": "masonry walls, 1 h interior", "III-B": "masonry walls, unprotected interior", "IV": "heavy timber / mass timber",
                           "V-A": "wood frame, 1 h", "V-B": "wood frame, unprotected"},
    "height_limit_m": {"_section": "IBC Table 504.3 (non-sprinklered)", "II-B": ft(55), "III-A": ft(65), "III-B": ft(55), "V-A": ft(50), "V-B": ft(40)},
    "stories_limit": {"_section": "IBC Table 504.4 (non-sprinklered)", "B": {"V-B": 2, "V-A": 3, "III-B": 3, "II-B": 3}, "M": {"V-B": 1, "V-A": 3, "III-B": 2, "II-B": 2},
                      "R-2": {"V-B": 2, "V-A": 3, "III-B": 3, "II-B": 3}, "A-2": {"V-B": 1, "V-A": 2, "III-B": 2, "II-B": 2}, "E": {"V-B": 1, "V-A": 1, "III-B": 2, "II-B": 2}},
    "egress": {"corridor_min_m": round(44 * 0.0254, 3), "door_clear_min_m": round(32 * 0.0254, 3), "stair_riser_max_m": round(7 * 0.0254, 3),
               "stair_tread_min_m": round(11 * 0.0254, 3), "stair_width_min_m": round(44 * 0.0254, 3), "headroom_min_m": round(80 * 0.0254, 3),
               "two_exits_over_occupants": 49, "travel_distance_max_m": {"B": ft(200), "M": ft(200), "R-2": ft(125)}, "_section": "IBC ch. 10"},
    "ceilings": {"habitable_min_m": round(7.5 * FT, 2), "_section": "IBC 1208.2"},
    "accessibility": {"accessible_route_clear_m": round(36 * 0.0254, 3), "ramp_max_slope": 1 / 12, "parking_accessible_per_25": 1, "van_aisle_m": ft(8), "_section": "IBC ch. 11 / ICC A117.1"},
    "residential": {"_section": "IRC as adopted (the Residential Code of Ohio)", "ceiling_min_m": round(7 * FT, 2), "stair_riser_max_m": round(7.75 * 0.0254, 3),
                    "stair_tread_min_m": round(10 * 0.0254, 3), "guard_height_min_m": round(36 * 0.0254, 3), "egress_window_min_m2": round(5.7 * FT * FT, 2),
                    "smoke_alarms": "each bedroom, outside each sleeping area, each storey", "garage_separation": "1/2-inch gypsum on the garage side"},
    "parking_lots": {"stall_m": [ft(9), ft(18)], "aisle_90deg_m": ft(24), "accessible_stall_m": ft(8), "accessible_aisle_m": ft(5), "landscape_island_every_stalls": 12},
}

# ------------------------------------------------------------------ the planning literature, reduced to rules the generator can use
SCHOLARSHIP = {
    "walkable": [
        ("Jacobs 1961", "The Death and Life of Great American Cities", "mixed primary uses, short blocks, buildings of mixed ages, density; eyes on the street; sidewalks as social places (20-35 ft where busy)"),
        ("Lynch 1960", "The Image of the City", "paths, edges, districts, nodes, landmarks: legible towns"),
        ("Gehl 1971 / 2010", "Life Between Buildings; Cities for People", "the human scale: ground floors with frequent doors, edges to linger, 5 km/h architecture"),
        ("Frank & Pivo 1994; Saelens, Sallis & Frank 2003", "Impacts of mixed use and density on driving, transit and walking; Environmental correlates of walking and cycling", "density, mix and connectivity raise walking; the walkability index"),
        ("Cervero & Kockelman 1997; Ewing & Cervero 2010", "Travel demand and the 3Ds; Travel and the Built Environment (meta-analysis, JAPA)", "the D variables: density, diversity, design, destination accessibility, distance to transit; intersection density and destination access matter most for walking"),
        ("Southworth 2005", "Designing the Walkable City (J. Urban Planning & Development)", "connectivity, linkage to other modes, fine-grained land use, safety, path quality, path context"),
        ("Speck 2012", "Walkable City", "the general theory of walkability: a walk must be useful, safe, comfortable and interesting"),
        ("Forsyth 2015", "What is a walkable place? (Urban Design International)", "walkability means different things: measure what you mean"),
    ],
    "urban": [
        ("Alexander et al. 1977", "A Pattern Language", "patterns from region to room: the 'network of paths and cars', 'promenade', 'small public squares'"),
        ("Whyte 1980", "The Social Life of Small Urban Spaces", "sittable space, sun, food, triangulation: what makes plazas used"),
        ("Calthorpe 1993", "The Next American Metropolis", "transit-oriented development: mixed-use within a 400-800 m walk of a stop"),
        ("Duany & Plater-Zyberk; CNU 1996", "Charter of the New Urbanism", "5-minute walk (400 m) neighbourhoods, connected streets, buildings to the street, parking behind"),
        ("Duany, Plater-Zyberk & Alminana 2003", "The New Civic Art; the Transect", "rural-to-urban transect zones T1-T6 set street and building form by place"),
        ("Glaeser 2011", "Triumph of the City", "density and proximity as the engine of exchange"),
    ],
    "suburban": [
        ("Warner 1962", "Streetcar Suburbs", "suburbs grew along the tram lines, lots within a walk of the car stop"),
        ("Jackson 1985", "Crabgrass Frontier", "the US suburb: transport, cheap land, FHA lending, and its costs"),
        ("Fishman 1987", "Bourgeois Utopias", "the suburb as an idea of the family retreat"),
        ("Southworth & Ben-Joseph 1997", "Streets and the Shaping of Towns and Cities", "how subdivision street standards (FHA 1930s, ITE) produced loops and cul-de-sacs, and wide streets"),
        ("Duany, Plater-Zyberk & Speck 2000", "Suburban Nation", "sprawl's costs; collector-street hierarchy versus the connected grid"),
        ("Hayden 2003", "Building Suburbia", "seven historical suburban landscapes, 1820-2000"),
        ("Dunham-Jones & Williamson 2009", "Retrofitting Suburbia", "turning malls and strips into walkable centres"),
        ("Radburn 1929; FHA 1936", "(plans and guidelines)", "the cul-de-sac superblock; FHA promotes curvilinear streets and cul-de-sacs"),
    ],
}
DESIGN_RULES = {
    "_about": "Rules the procedural generator applies, each from the literature (SCHOLARSHIP) and the ordinances.",
    "walk_radius_m": 400, "transit_walk_radius_m": 800,
    "core_block_max_m": ft(400), "town_block_max_m": ft(600),
    "intersection_density_target_per_km2": 100,
    "core_frontage": "build to the back of the sidewalk; doors every 10-15 m; parking behind or in public lots",
    "town_frontage": "front yards per the zoning district; garages behind the front wall",
    "sidewalks": "both sides of every town street (the cities' codes); ADA clear 1.2 m minimum (PROWAG), passing space every 60 m on 1.2 m walks; cross slope 2 % max",
    "tree_lawn": "between kerb and walk on residential streets: trees every 12 m",
    "parking_lots": "downtown: behind the street wall, never at a corner; park-and-ride at the edge of town on a tram stop",
    "park_and_ride": {"at": "a tram stop at the edge of each city and town, on the trunk road in", "spaces": [40, 150], "walk_to_stop_max_m": 120},
    "cul_de_sac": "only where land allows nothing else; under 183 m; a footpath through to the next street where possible (Southworth & Ben-Joseph)",
}
