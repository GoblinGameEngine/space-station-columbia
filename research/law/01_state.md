# 1. The state baselines

## the Ohio Revised Code (as carried aboard: the Charter's Code of the Road, art. 30)

**Speeds:** school_zone_mph 20, business_district_mph 25, urban_district_mph 25, alley_mph 15, state_route_in_town_mph 35, source ORC 4511.21, basis fetched

**No parking (ORC 4511.68 (fetched)):**

- sidewalk
- in front of driveway
- within intersection
- from hydrant -- 3.0 m
- on crosswalk
- from crosswalk at intersection -- 6.1 m
- before stop yield or signal -- 9.1 m
- opposite safety zone ends -- 9.1 m
- from rail crossing -- 15.2 m
- from fire station driveway -- 6.1 m
- opposite fire station -- 22.9 m
- beside excavation
- double parking
- bridge or tunnel
- where signed
- from parked vehicle -- 0.3 m
- freeway roadway
- bicycle lane

**Parking position:** {"max_from_curb_m": 0.3, "side": "right, with the flow", "one_way_left_by_ordinance": true, "angle_by_ordinance_only": true, "angle_min_clear_roadway_m": 7.62, "disability_extra_hours": 2, "disability_fine_usd": [250, 500], "source": "ORC 4511.69 (fetched)"}

**Sidewalks:** the abutting owner builds and repairs sidewalks, curbs and gutters; the city may order it and, if not done, do it and assess the cost on the lot

**Subdivisions:** {"approval_outside_towns": "the county commissioners (here: the Regional Planning Board of the governing city)", "decision_days": 30, "deemed_approved_if_late": true, "min_lot_sqft_floor": 4800, "appeal_days": 60, "rules_may_cover": ["street arrangement and coordination", "open spaces for traffic, utilities, fire access, recreation, light and air", "avoiding congestion", "health board review", "sewage rules"], "source": "ORC 711.05, 711.10 (fetched)"}

**Building:** {"state_code": "the Ohio Building Code (OAC 4101:1; the International Building Code as amended)", "residential_code": "the Residential Code of Ohio (OAC 4101:8; the International Residential Code as amended)", "local_additions": "a city may add regulations that don't conflict; the Board of Building Standards may void a conflicting one not needed for health or safety (ORC 3781.01, fetched)"}

## the Indiana Code (as carried aboard: the Oceanview Compact's Indiana charter, a founders' inheritance)

**Speeds:** urban_district_mph 30, alley_mph 15, school_zone_mph 20, source IC 9-21-5-2 (knowledge), basis knowledge

**No parking (IC 9-21-16-5 (knowledge)):**

- sidewalk
- in front of driveway
- within intersection
- from hydrant -- 4.6 m
- on crosswalk
- from crosswalk at intersection -- 6.1 m
- before stop yield or signal -- 9.1 m
- from rail crossing -- 15.2 m
- from fire station driveway -- 6.1 m
- opposite fire station -- 22.9 m
- double parking
- bridge or tunnel
- where signed

**Parking position:** {"max_from_curb_m": 0.3, "side": "right, with the flow", "source": "IC 9-21-16-3 (knowledge)"}

**Sidewalks:** the abutting owner keeps the sidewalk; the city may build and assess (IC 36-9 (knowledge))

**Subdivisions:** {"approval": "the plan commission under the subdivision control ordinance (IC 36-7-4-700, knowledge)"}

**Building:** {"state_code": "the Indiana Building Code (675 IAC 13; the IBC as amended)", "residential_code": "the Indiana Residential Code (675 IAC 14; the IRC as amended)"}

