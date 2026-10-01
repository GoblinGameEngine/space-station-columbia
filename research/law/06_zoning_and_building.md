# 6. Zoning and the building code

Zoning districts (each city's zoning code; the station's values, in the range the basis cities use, from knowledge). Setbacks in metres; heights in metres; parking per unit / per 100 m2.

| district | use | front m | side m | rear m | height m | coverage |
|---|---|---|---|---|---|---|
| R-1 | single-family | 7.62 | 1.83 | 9.14 | 10.67 | 0.35 |
| R-2 | one- and two-family | 6.1 | 1.52 | 7.62 | 10.67 | 0.4 |
| R-3 | townhouses and small apartments | 4.57 | 0.0 | 6.1 | 13.72 | 0.55 |
| C-1 | neighbourhood commercial | 0.0 | 0.0 | 4.57 | 13.72 | 0.8 |
| C-2 | downtown core (form-based: build to the back of the sidewalk) | 0.0 | 0.0 | 3.05 | 25.91 | 1.0 |
| M-1 | light industry, the Works | 9.14 | 4.57 | 6.1 | 18.29 | 0.6 |
| P | parks, schools, civic | 9.14 | 6.1 | 6.1 | 13.72 | - |
| A | agriculture | 15.24 | 7.62 | 15.24 | 10.67 | - |

## Building code tokens

Tokens from the state building codes for the procedural generator: the Ohio Building Code (OAC 4101:1, the IBC as amended) and the Residential Code of Ohio (OAC 4101:8, the IRC as amended), and Indiana's (675 IAC 13 / 14). The adoption is fetched (ORC 3781.01, OAC rule pages); the numeric provisions are the model codes' as widely published (from knowledge -- the ICC texts are copyrighted and were not fetched). Each value names its section.

- **occupancy_groups:** {"A": "assembly (theatres, churches, restaurants over 50)", "B": "business (offices, clinics)", "E": "educational (schools)", "F": "factory", "H": "high hazard", "I": "institutional (hospitals, care)", "M": "mercantile (stores)", "R-1": "transient (hotels, motels)", "R-2": "apartments (3+ units)", "R-3": "one- and two-family (outside the residential code)", "S": "storage", "U": "utility (garages, sheds)"}
- **construction_types:** {"I-A": "non-combustible, 3 h frame", "I-B": "non-combustible, 2 h", "II-A": "non-combustible, 1 h", "II-B": "non-combustible, unprotected", "III-A": "masonry walls, 1 h interior", "III-B": "masonry walls, unprotected interior", "IV": "heavy timber / mass timber", "V-A": "wood frame, 1 h", "V-B": "wood frame, unprotected"}
- **height_limit_m:** {"_section": "IBC Table 504.3 (non-sprinklered)", "II-B": 16.76, "III-A": 19.81, "III-B": 16.76, "V-A": 15.24, "V-B": 12.19}
- **stories_limit:** {"_section": "IBC Table 504.4 (non-sprinklered)", "B": {"V-B": 2, "V-A": 3, "III-B": 3, "II-B": 3}, "M": {"V-B": 1, "V-A": 3, "III-B": 2, "II-B": 2}, "R-2": {"V-B": 2, "V-A": 3, "III-B": 3, "II-B": 3}, "A-2": {"V-B": 1, "V-A": 2, "III-B": 2, "II-B": 2}, "E": {"V-B": 1, "V-A": 1, "III-B": 2, "II-B": 2}}
- **egress:** {"corridor_min_m": 1.118, "door_clear_min_m": 0.813, "stair_riser_max_m": 0.178, "stair_tread_min_m": 0.279, "stair_width_min_m": 1.118, "headroom_min_m": 2.032, "two_exits_over_occupants": 49, "travel_distance_max_m": {"B": 60.96, "M": 60.96, "R-2": 38.1}, "_section": "IBC ch. 10"}
- **ceilings:** {"habitable_min_m": 2.29, "_section": "IBC 1208.2"}
- **accessibility:** {"accessible_route_clear_m": 0.914, "ramp_max_slope": 0.08333333333333333, "parking_accessible_per_25": 1, "van_aisle_m": 2.44, "_section": "IBC ch. 11 / ICC A117.1"}
- **residential:** {"_section": "IRC as adopted (the Residential Code of Ohio)", "ceiling_min_m": 2.13, "stair_riser_max_m": 0.197, "stair_tread_min_m": 0.254, "guard_height_min_m": 0.914, "egress_window_min_m2": 0.53, "smoke_alarms": "each bedroom, outside each sleeping area, each storey", "garage_separation": "1/2-inch gypsum on the garage side"}
- **parking_lots:** {"stall_m": [2.74, 5.49], "aisle_90deg_m": 7.32, "accessible_stall_m": 2.44, "accessible_aisle_m": 1.52, "landscape_island_every_stalls": 12}
