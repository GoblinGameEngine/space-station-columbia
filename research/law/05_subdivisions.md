# 5. Subdivisions

Subdivision rules the station's Regional Planning Boards apply (ORC 711.10 lets the board make them; Indiana's plan commissions likewise). Values are the station's, in the range Ohio and Indiana county regulations use (from knowledge; the county regulations themselves were not fetched). Each city may override a value (CITY_SUBDIVISION).

- **local street:** {"row_m": 15.24, "pavement_back_to_back_m": 8.53, "parking": "one side", "sidewalks": "both sides, 5 ft, 4 ft tree lawn", "curb_radius_m": 7.62, "speed_kmh": 40}
- **collector:** {"row_m": 18.29, "pavement_back_to_back_m": 10.97, "parking": "both sides or none", "sidewalks": "both sides, 5 ft"}
- **cul de sac:** {"max_length_m": 182.88, "max_lots": 20, "turnaround_pavement_radius_m": 12.19, "turnaround_row_radius_m": 15.24, "sign": "W14-2 NO OUTLET at its mouth"}
- **loop street:** {"max_length_m": 731.52, "sign": "W14-2 NO OUTLET where its only way out is one entrance"}
- **blocks:** {"max_length_m": 402.34, "min_length_m": 121.92, "mid_block_walk_when_longer_than_m": 274.32}
- **intersections:** {"min_angle_deg": 75, "min_offset_m": 38.1, "max_legs": 4, "stop_control": "STOP (R1-1) on the subdivision street where it meets a collector or arterial; no all-way stops in the subdivision"}
- **access:** {"min_entrances_over_lots": [[30, 2]], "stub_to_adjoining_land": true}
- **lots:** {"min_frontage_m": 18.29, "min_area_m2": 446, "corner_lot_extra_width_m": 3.05}
- **signs:** {"street_name": "D3-1 at every intersection, both streets", "speed_limit": "R2-1 at each entrance (40 km/h = 25 mph)", "no_outlet": "W14-2 at a cul-de-sac's or one-entrance loop's mouth", "stop": "R1-1 on the minor leg", "school": "S1-1 where a school fronts"}
- **required improvements:** ["paved streets with curb and gutter", "sidewalks both sides", "street trees every 40 ft in the tree lawn", "street lights at intersections and every 200 ft", "storm sewers", "monuments at block corners"]
