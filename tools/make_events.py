#!/usr/bin/env python3
"""The station's calendar of crowd-drawing events (godot_project/remake/events.json), read by
TransitDemand (remake/scripts/transit/transit_demand.gd): where people go, when.

    python3 tools/make_events.py

From the bible's holidays (remake/bible/culture.json) and the cities' ordinances (remake/law): each
event says where it draws people (a town, or "*" for every town square), on which days (a rule), in
which hours, and how strongly (draw: the town counts this many times its own population more).
The rules: {"md": "MM-DD"} a date; {"md_range": ["MM-DD", "MM-DD"]}; {"nth": [n, weekday, month]}
(n -1 = the last; weekday 0 = Monday); {"sat_near": "MM-DD"}; {"weekly": [weekdays]}, with
{"months": [..]} to limit any rule to a season.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "godot_project", "remake", "events.json")

EVENTS = [
    # the bible's holidays that draw crowds to a place
    ("launch_day", "Launch Day", "Kessler", {"md": "04-21"}, [9, 22], 2.5, "the Launch Bell at Kessler; parades in every town"),
    ("launch_day_towns", "Launch Day parades", "*", {"md": "04-21"}, [10, 14], 0.8, "parades in every town"),
    ("waymakers_vigil", "the Waymakers' Vigil", "*", {"md": "04-20"}, [20, 30], 0.5, "an all-night vigil facing north"),
    ("charter_day", "Charter Day", "*", {"md": "07-04"}, [9, 23], 1.2, "the Charter read on every town square; fireworks at the early dusk"),
    ("charter_parade", "Charter Day parade", "Kessler", {"md": "07-04"}, [6, 13], 2.0, "the parade route (Kessler ordinances)"),
    ("dyngus_day", "Dyngus Day", "Port Carrow", {"easter_monday": True}, [10, 24], 2.0, "Hedwig Hill throws the station's biggest"),
    ("midsummer_regatta", "the Midsummer Regatta", "Port Tamsin", {"sat_near": "07-20"}, [8, 20], 3.0, "races on Lake Tamsin and the seas"),
    ("regatta_week", "Regatta Week", "Port Carrow", {"md_range": ["07-14", "07-20"]}, [10, 22], 0.8, "the Lakeshore Road kerbs closed (Port Carrow ordinances)"),
    ("fiesta_de_rosario", "the Fiesta de Rosario", "Solana Point", {"nth": [2, 5, 8], "span_days": 2}, [11, 26], 2.5, "the Solano procession, dancing on the Malecon"),
    ("northland_fair", "the Northland Fair", "Marlowe", {"md_range": ["08-25", "08-31"]}, [9, 22], 3.0, "livestock shows, the midway, tractor pulls"),
    ("labor_day", "Labor Day (the Union Parade)", "Port Carrow", {"nth": [1, 0, 9]}, [9, 17], 1.5, "the Cannery and Dock Workers' parade"),
    ("forty_days", "the Forty Days march", "Tern Harbor", {"nth": [1, 0, 9]}, [9, 15], 1.5, "the Tern Harbor march (since VY 429)"),
    ("saint_jean", "Saint-Jean-Baptiste Day", "Port Carrow", {"md": "06-24"}, [18, 26], 1.0, "bonfires on the beach, Carrow French songs"),
    ("tamsins_day", "Tamsin's Day", "Port Tamsin", {"md": "06-12"}, [9, 17], 1.5, "blessings of babies at the lake"),
    ("return_day", "Return Day", "*", {"nth": [-1, 0, 5]}, [9, 17], 0.6, "the memorial groves; the first swim of summer"),
    ("new_year", "New Year's Eve", "*", {"md": "12-31"}, [20, 26], 0.8, "late parties"),
    ("thanksgiving", "the Thanksgiving spinball games", "Solana Point", {"nth": [4, 3, 11]}, [11, 18], 1.5, "the games at the Sun Bowl"),
    ("halloween", "Halloween", "*", {"md": "10-31"}, [17, 24], 0.5, "trick-or-treat"),
    # the cities' ordinances: the regular crowds
    ("suns_game_day", "Suns game day", "Solana Point", {"weekly": [5]}, [11, 18], 1.2, "spinball at the Sun Bowl (Solana Point ordinances)"),
    ("falls_shift_am", "the Falls Yard shift change", "Harrow Falls", {"weekly": [0, 1, 2, 3, 4]}, [5.5, 7], 0.8, "the Works' early shift (Harrow Falls ordinances)"),
    ("falls_shift_pm", "the Falls Yard shift change", "Harrow Falls", {"weekly": [0, 1, 2, 3, 4]}, [14.5, 16], 0.8, "the Works' day shift out"),
    ("harbour_loading", "harbour loading", "Port Carrow", {"weekly": [0, 1, 2, 3, 4, 5]}, [6, 10], 0.3, "the dock streets (Port Carrow ordinances)"),
    ("beach_season", "the beach season", "Brightwater", {"weekly": [5, 6], "months": [6, 7, 8]}, [10, 19], 1.0, "summer-season beach lots (Brightwater ordinances)"),
    ("ocean_road_nights", "Ocean Road nights", "Oceanview", {"weekly": [4, 5]}, [20, 26], 0.8, "the strip (Oceanview ordinances)"),
    ("fish_fry", "the Friday fish fry", "*", {"weekly": [4]}, [17, 21], 0.2, "every tavern, church and lodge"),
]


def main():
    out = {"_about": __doc__.strip().split("\n")[0], "start_date": "2752-05-24", "start_weekday": 2,
           "events": [{"id": e[0], "name": e[1], "town": e[2], "when": e[3], "hours": e[4], "draw": e[5], "what": e[6]} for e in EVENTS]}
    json.dump(out, open(OUT, "w"), indent=1)
    print("events:", len(EVENTS), "->", OUT)


if __name__ == "__main__":
    main()
