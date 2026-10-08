#!/usr/bin/env python3
"""towns.py -- every settlement at 1:1 (the user, 2026-10-07), as specs for city.py: population (the design pop of the
inventories), tier, region style, archetype, civic heart, waterfront and landmarks (research/terrain_and_cities/README.md
section 7).  Calder keeps its own plan (calder.py) and is not here.

Regions: "ne" -- the North Sea's rocky New England shore and its near settlements; "ca" -- the South Sea's sandy California
shore and its near settlements; "gl" -- the Great Lakes / Midwest country toward the river.  A town's lots blend toward
"gl" with distance from the coast (regions.region_mix).

Positions: s round the ring; x along the axis.  A coastal town's x is set by the map from its harbour's waterline (SITE);
an inland town's x is given (the map's old anchors, kept where the roads and the rail already meet them).
"""

SPECS = [
    # ---- the cities
    dict(name="Solana Point", pop=44200, tier="city", region="ca", side=1, coast=True, archetype="harbor_city", waterfront=True,
         heart="plaza", seed=101, prefix="SOL",
         character="the Santa Barbara / Dana Point of the South Sea: a Spanish city round its plaza and mission, its harbour "
                   "behind the point, the long pier off the beach",
         landmarks=[dict(kind="mission", label="Mission Solana", near="heart", size=(60, 46)),
                    dict(kind="courthouse_tower", label="Solana County Courthouse", near="heart", size=(70, 46)),
                    dict(kind="paseo", label="El Paseo", near="downtown"),
                    dict(kind="pier", label="Solana Pier", length=420.0, near="beach"),
                    dict(kind="harbor", label="Solana Harbor", near="point"),
                    dict(kind="lighthouse", label="Point Solana Light", near="point"),
                    dict(kind="bluff_park", label="Headlands Park", near="point")]),
    dict(name="Harrow Falls", pop=41800, tier="city", region="gl", side=1, coast=False, archetype="falls_city", waterfront=True,
         heart="square", seed=102, prefix="HF", s=7900.0, x=934.0, hilly=True, lake=True,
         character="the Duluth of the station: a lake-bluff city wrapped round Harrow Hill, the falls dropping from the hill's "
                   "cliff into Falls Park, the incline up the hill, the stone lookout on its summit, stairs everywhere",
         landmarks=[dict(kind="falls_park", label="Falls Park", near="falls"),
                    dict(kind="mill_lofts", label="Old Mill Lofts", near="falls"),
                    dict(kind="incline", label="Harrow Hill Incline", near="hill"),
                    dict(kind="lookout_tower", label="Lookout Tower", near="summit"),
                    dict(kind="breakwater_light", label="Harrow Falls Breakwater Light", near="lake"),
                    dict(kind="lake_bridge", label="Tamsin Bridge", near="island")]),
    dict(name="Port Carrow", pop=38600, tier="city", region="ne", side=-1, coast=True, archetype="port_city", waterfront=True,
         heart="green", seed=103, prefix="PCR", hilly=True,
         character="the Portland, Maine of the North Sea: a granite-and-brick port on a rocky harbour, the Old Port's wharves, "
                   "the signal tower on the hill, the customs house, the promenade along the headland",
         landmarks=[dict(kind="signal_tower", label="Carrow Signal Tower", near="hill"),
                    dict(kind="custom_house", label="Custom House", near="wharves", size=(46, 34)),
                    dict(kind="old_port", label="The Old Port", near="downtown"),
                    dict(kind="wharves", label="Commercial Wharves", near="harbor"),
                    dict(kind="fish_pier", label="Fish Pier", near="harbor"),
                    dict(kind="lighthouse", label="Carrow Head Light", near="headland"),
                    dict(kind="promenade_park", label="Eastern Promenade", near="headland")]),
    dict(name="Kessler", pop=34500, tier="city", region="gl", side=1, coast=False, archetype="rail_city", waterfront=False,
         heart="square", square_landmark="city_hall_deco", seed=104, prefix="K", s=42609.0, x=2058.0, rail=True,
         character="a Midwest rail and works city on the flat plain: Union Station's clock tower, the yards and roundhouse, "
                   "the Kessler Works' stacks, the Art Deco city hall, Sauk Park's pond",
         landmarks=[dict(kind="union_station", label="Kessler Union Station", near="rail", size=(80, 30)),
                    dict(kind="roundhouse", label="Roundhouse", near="rail"),
                    dict(kind="works", label="Kessler Works", near="rail", size=(220, 140)),
                    dict(kind="park_pond", label="Sauk Park", near="edge", size=(260, 200)),
                    dict(kind="ballpark", label="Works Field", near="edge", size=(150, 150)),
                    dict(kind="water_tower", label="Kessler water tower", near="edge")]),
    # ---- towns of 9,000+ (their own characters)
    dict(name="Oceanview", pop=9800, tier="town", region="ca", side=1, coast=True, archetype="boardwalk_resort", waterfront=True,
         heart="plaza", seed=105, prefix="OCV",
         character="the Santa Cruz of the South Sea: the Beach Boardwalk with its carousel and casino, the wharf, Mission-style hotels",
         landmarks=[dict(kind="boardwalk", label="Beach Boardwalk", near="beach"),
                    dict(kind="carousel", label="The Carousel", near="beach"),
                    dict(kind="casino", label="The Casino", near="beach", size=(70, 40)),
                    dict(kind="pier", label="Municipal Wharf", length=300.0, near="beach"),
                    dict(kind="lighthouse", label="Lighthouse Point", near="point")]),
    dict(name="Marlowe", pop=9100, tier="town", region="gl", side=-1, coast=False, archetype="county_seat", waterfront=False,
         heart="square", seed=106, prefix="M", s=30004.0, x=-2030.0,
         character="the county seat on its courthouse square (the Upper South's Shelbyville square): the domed courthouse, "
                   "the opera house, the Carnegie library",
         names={"courthouse": "Brannock County Courthouse"},
         landmarks=[dict(kind="opera_house", label="Marlowe Opera House", near="heart", size=(30, 40)),
                    dict(kind="water_tower", label="Marlowe water tower", near="edge")]),
    # ---- towns
    dict(name="Tamarack", pop=8300, tier="town", region="gl", side=1, coast=False, archetype="mill_town", seed=107, prefix="T",
         s=56406.0, x=2118.0, heart="square"),
    dict(name="Bellhaven", pop=7200, tier="town", region="gl", side=1, coast=False, archetype="rail_town", seed=108, prefix="B",
         s=21011.0, x=2045.0, rail=True, heart="square", institutions={"college": 1}),
    dict(name="Fenwick", pop=6400, tier="town", region="gl", side=-1, coast=False, archetype="college_town", seed=109, prefix="F",
         s=43019.0, x=-2060.0, heart="green", landmarks=[dict(kind="college", label="Fenwick College", near="edge", size=(320, 220))]),
    dict(name="Brightwater", pop=6200, tier="town", region="ne", side=-1, coast=True, archetype="resort_town", waterfront=True,
         seed=110, prefix="BRW", heart="green"),
    dict(name="Playa Verde", pop=5400, tier="town", region="ca", side=1, coast=True, archetype="pier_town", waterfront=True,
         seed=111, prefix="PLV", heart="plaza", landmarks=[dict(kind="pier", label="Playa Verde Pier", length=380.0, near="beach")]),
    dict(name="Haven Point", pop=3900, tier="town", region="ne", side=-1, coast=True, archetype="inlet_harbor", waterfront=True,
         seed=112, prefix="HVN", heart="green", landmarks=[dict(kind="lighthouse", label="Haven Point Light", near="headland")]),
    dict(name="Port Tamsin", pop=3400, tier="town", region="gl", side=-1, coast=False, archetype="lake_resort", waterfront=True,
         seed=113, prefix="PTM", s=7998.0, x=-1935.0, lake=True, heart="green"),
    # ---- villages
    dict(name="Haskins Corner", pop=2600, tier="village", region="gl", side=-1, coast=False, archetype="crossroads", seed=114, prefix="HC",
         s=59113.0, x=-1837.0),
    dict(name="Pelican Cove", pop=1600, tier="village", region="ca", side=1, coast=True, archetype="fishing_village", waterfront=True,
         seed=115, prefix="PEL", heart="plaza"),
    dict(name="Tern Harbor", pop=1300, tier="village", region="ne", side=-1, coast=True, archetype="fishing_village", waterfront=True,
         seed=116, prefix="TRN", heart="green"),
    dict(name="Cedar Ford", pop=1150, tier="village", region="gl", side=-1, coast=False, archetype="mill_village", seed=117, prefix="CF",
         s=24974.0, x=-674.0),
    dict(name="Victory Bay", pop=900, tier="village", region="isle", upscale=True, side=-1, coast=False, archetype="island_village", waterfront=True,
         seed=118, prefix="VBY", island=True, lake=True, s=7700.0, x=-600.0, heart="green",
         character="the lake's wooded island (the user, 2026-10-07: 'a lot of trees and a big bridge with the mainland ... "
                   "shopping'): the village round its harbour, Island Market, the Tamsin Bridge to Harrow Falls",
         landmarks=[dict(kind="island_market", label="Island Market", near="downtown", size=(70, 40)),
                    dict(kind="grand_arcade", label="The Grand Arcade", near="heart", size=(80, 34)),
                    dict(kind="victory_column", label="Victory Column", near="point")]),
    dict(name="Pruett", pop=820, tier="village", region="gl", side=1, coast=False, archetype="rail_village", seed=119, prefix="P",
         s=29988.0, x=2359.0, rail=True),
    dict(name="Dunmore Crossing", pop=480, tier="village", region="gl", side=-1, coast=False, archetype="crossroads", seed=120, prefix="DC",
         s=13009.0, x=-2059.0),
    dict(name="Loomis Grove", pop=390, tier="village", region="gl", side=-1, coast=False, archetype="crossroads", seed=121, prefix="LG",
         s=51596.0, x=-2937.0),
]

BY_NAME = {s["name"]: s for s in SPECS}
