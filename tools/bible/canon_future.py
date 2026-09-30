"""Columbia game bible: the future, VY 500-3000 (2752-5252). Sparse by design: what the engine may
need to foreshadow (hooks), and the shape of the station's end. Nobody aboard in VY 500 knows any of
this; every entry is known='lost'. Story use: prophecy, rumour, the Steward's hints, Waymaker
visions -- never facts a character can state.
"""

FUTURE_ERAS = [
    dict(id="the_waking", name="the Waking", vy=[500, 612], ad=[2752, 2864],
         summary="after the Notice, curiosity grows; the Wardens' Library circle becomes a movement; the Steward answers petitions for the first time (VY 537)"),
    dict(id="the_second_opening", name="the Second Opening", vy=[612, 750], ad=[2864, 3002],
         summary="the Steward reopens the Undercroft to trained people (the new Wardens); the station relearns itself; the Earth Heartbeat is decoded"),
    dict(id="the_midpoint", name="the Midpoint", vy=[750, 1100], ad=[3002, 3352],
         summary="halfway: the Midpoint Festival; slow change; a second Troubles over the shares (VY 910s)"),
    dict(id="the_seeing", name="the Seeing", vy=[1100, 1469], ad=[3352, 3721],
         summary="the destination star is shown on the Boards, brightening year by year; preparation"),
    dict(id="the_long_brake", name="the Long Brake", vy=[1469, 1500], ad=[3721, 3752],
         summary="the drive wakes; thirty years of braking; the seas lean a hair to the south"),
    dict(id="arrival", name="Arrival", vy=[1500, 1523], ad=[3752, 3775], summary="Columbia reaches Alpha Centauri A and orbits Hesper; surveys"),
    dict(id="the_divide", name="the Divide", vy=[1523, 1700], ad=[3775, 3952], summary="Planetfall; those who go down and those who stay; the station becomes 'the Old Country'"),
    dict(id="the_old_country", name="the Old Country", vy=[1700, 2950], ad=[3952, 5202], summary="the station as a heritage world in orbit, its population slowly falling"),
    dict(id="the_long_evening", name="the Long Evening", vy=[2950, 3000], ad=[5202, 5252],
         summary="the Steward's three-thousand-year service life (the Long Clause) ends; it powers down in stages; the last residents leave; the station is abandoned"),
]

FUTURE_EVENTS = [
    dict(id="first_answer", vy=537, kind="steward", summary="the Steward answers a petition for the first time: a list of the station's systems and their condition", hook_for_present="the Notice suggests the Steward may speak"),
    dict(id="imogen_found", vy=541, kind="mystery", summary="the truth of Imogen Sato-Ferris (left for the story engine to decide; the bible reserves it)", hook_for_present="the Bellhaven Dig"),
    dict(id="second_opening", vy=612, kind="steward", summary="the Second Opening: trained people allowed into the Undercroft; the Wardens re-founded", hook_for_present="the Open Hand's demands"),
    dict(id="heartbeat_decoded", vy=640, kind="contact", summary="the Heartbeat decoded: Earth has been sending its history for two hundred years", hook_for_present="the Heartbeat"),
    dict(id="midpoint_festival", vy=750, kind="festival", summary="the Midpoint (2 March 3002): the station's greatest festival", hook_for_present="'a third of the way'"),
    dict(id="second_troubles", vy=912, kind="conflict", summary="the second Troubles: the shares fought over; the Balance holds", hook_for_present="the Registry Leak"),
    dict(id="the_seeing_begins", vy=1100, kind="discovery", summary="the Boards begin showing the destination star", hook_for_present="the Waymakers' hope"),
    dict(id="kaveri_contact", vy=1340, kind="contact", summary="the ark Kaveri's signal detected, following", hook_for_present="the Waymaker belief in 'the ship behind us'"),
    dict(id="brake_begins", vy=1469, kind="voyage", summary="the drive wakes for the Long Brake", hook_for_present="Coasting Day"),
    dict(id="arrival_hesper", vy=1500, kind="arrival", summary="arrival at Alpha Centauri A (21 April 3752); orbit round Hesper", hook_for_present="the Notice's 'two thirds'"),
    dict(id="planetfall", vy=1523, kind="migration", summary="Planetfall: the first 3,000 go down to Hesper", hook_for_present="the Far Shore"),
    dict(id="the_divide_vote", vy=1561, kind="political", summary="the Divide: the station votes to remain a home for those who stay", hook_for_present="the Referendum of VY 262"),
    dict(id="last_census_250k", vy=1640, kind="demography", summary="the last census at the Balance; the population falls after", hook_for_present="the Balance"),
    dict(id="old_country", vy=1800, kind="culture", summary="the station called 'the Old Country' on Hesper; pilgrimages to Port Carrow", hook_for_present="heritage pride"),
    dict(id="long_clause_notice", vy=2950, kind="steward", summary="the Notice of the Long Clause: SERVICE LIFE ENDS IN FIFTY YEARS", hook_for_present="the Steward's design (scholar knowledge)"),
    dict(id="last_launch_day", vy=2999, kind="festival", summary="the last Launch Day aboard", hook_for_present="Launch Day"),
    dict(id="abandonment", vy=3000, kind="ending", summary="the Steward powers down; the last residents descend to Hesper; Columbia is abandoned in orbit (21 April 5252)", hook_for_present="none: the end"),
]
