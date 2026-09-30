#!/usr/bin/env python3
"""Writes the role catalogue: research/roles/roles.json (engine) and research/roles/04_role_catalogue.md.

    python3 tools/story/make_roles.py

Each role: family, kind (ascribed / achieved / emergent), frequency (per 1,000 residents, or per
settlement, or a rule for emergent roles), prestige 1-5 (anchored on NORC/GSS prestige), prominence
0-1 (how much the town talks about them: salience in propagation), class (business / working / none),
knowledge channels (what the role knows without being told), role set (whom it deals with: adds
ties and relational models), duties (event verbs), story hooks (story_types.json ids -- validated),
eligibility, personality lean, typical strain, and its station form.
Per-1,000 figures for occupations: BLS OEWS May 2024 counts / 335 M residents where quoted in
research/roles/02 section 2.2; the rest are estimates at BLS magnitudes (marked est=True).
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
STORY_IDS = {t["id"] for t in json.load(open(os.path.join(ROOT, "research", "story", "story_types.json")))["story_types"]}
R = []


def role(fam, id, name, kind, freq, prestige, prominence, cls, knows, rset, duties, hooks, eligible, lean="", strain="",
         station="", sources="", est=True):
    R.append(dict(family=fam, id=id, name=name, kind=kind, freq=freq, prestige=prestige, prominence=prominence, cls=cls,
                  knows=knows, set=rset, duties=duties, hooks=hooks, eligible=eligible, lean=lean, strain=strain,
                  station=station, sources=sources, estimate=est))


P = lambda x: {"per1000": x}          # noqa: E731  frequency per 1,000 residents
S = lambda x: {"per_settlement": x}   # noqa: E731
RULE = lambda x: {"rule": x}          # noqa: E731

# -- A. household and kin (ascribed; from the household generator) --------------------------------
A = "A household and kin"
role(A, "parent", "Parent", "ascribed", RULE("household member with children"), 0, 0.1, "none", ["their children's lives and friends"], ["children", "other parents", "teachers"], ["care", "discipline", "provide"], ["coming_of_age", "runaway", "sacrifice_for_kin", "rivalry_of_kin"], "adult with child in household", strain="parent + work shift (role conflict)", sources="households")
role(A, "spouse", "Spouse / partner", "ascribed", RULE("married or partnered adult"), 0, 0.05, "none", ["partner's moods, money, secrets"], ["partner", "in-laws"], ["share", "support", "argue"], ["infidelity", "mistaken_jealousy", "estrangement", "grief"], "partnered adult", sources="Census 2024: 74% of family households married couples")
role(A, "child", "Child", "ascribed", RULE("age < 13"), 0, 0.05, "none", ["what adults say in front of them", "hiding places"], ["parents", "siblings", "classmates", "teacher"], ["play", "explore", "ask"], ["curiosity", "lost_and_found", "wonder"], "age < 13", lean="O+ (curiosity)", station="children see the station as normal: no Earthsickness")
role(A, "teen", "Teenager", "ascribed", RULE("age 13-19"), 0, 0.1, "none", ["other teens' secrets", "places adults don't go"], ["parents", "peers", "teachers", "coach"], ["rebel", "test", "flirt", "work part-time"], ["coming_of_age", "runaway", "courtship", "temptation"], "age 13-19", strain="little to do (Gans)", station="born-here teens: no memory of Earth; restless in a small world", sources="Gans 1967")
role(A, "grandparent", "Grandparent", "ascribed", RULE("elder with grandchildren"), 0, 0.15, "none", ["family history", "old grudges"], ["children", "grandchildren"], ["remember", "advise", "babysit"], ["caring_for_elder", "identity_revealed", "grief"], "elder with grandchildren in the settlement")
role(A, "sibling", "Sibling", "ascribed", RULE("shares parents with another resident"), 0, 0.05, "none", ["the family's version of events"], ["siblings", "parents"], ["compete", "protect", "tease"], ["rivalry_of_kin", "feud_in_family", "recovery_of_lost_one"], "has a sibling")
role(A, "caregiver", "Family caregiver", "ascribed", P(250 / 1.3), 0, 0.1, "none", ["the cared-for person's health and needs", "the clinic's routines"], ["cared-for", "doctor", "home aide"], ["care", "fetch", "worry"], ["caring_for_elder", "sacrifice_for_kin", "crisis_and_recovery"], "adult with a dependent elder or disabled kin", strain="care + job + own family (overload)", sources="AARP 2025: 63 M caregivers, about 1 in 4 adults", est=False)
role(A, "kinkeeper", "Kin-keeper", "ascribed", RULE("one per extended family: highest communion x A, usually an older woman"), 0, 0.3, "none", ["everyone in the family's news", "birthdays, feuds, who isn't speaking"], ["the whole kin network"], ["call", "visit", "host holidays", "mend"], ["forgiveness", "festival", "estrangement", "letters"], "adult in an extended family", lean="A+, E+, communion+", sources="di Leonardo 1987")
role(A, "breadwinner", "Breadwinner", "ascribed", RULE("main earner of a household with dependents"), 0, 0.05, "none", ["the household's money troubles"], ["employer", "household"], ["work", "provide"], ["sacrifice_for_kin", "temptation", "hard_choice"], "earner with dependents", strain="job loss threatens identity")
role(A, "homemaker", "Homemaker", "ascribed", P(15), 1, 0.15, "none", ["the street's comings and goings"], ["household", "neighbours", "school"], ["cook", "keep house", "organise"], ["small_kindness", "festival", "found_family"], "adult not in paid work, running a household", sources="existing table (homemaker)")
role(A, "widow", "Widow / widower", "ascribed", RULE("spouse deceased"), 0, 0.15, "none", ["the dead spouse's secrets"], ["kin", "church"], ["grieve", "remember"], ["grief", "courtship", "caring_for_elder"], "partner died")
role(A, "single", "Single, living alone", "ascribed", RULE("one-person household"), 0, 0.0, "none", [], ["friends", "coworkers"], ["work", "go out"], ["courtship", "friendship", "found_family"], "one-person household", sources="Census 2024: 29% of households are one person", est=False)
role(A, "black_sheep", "Black sheep", "emergent", RULE("family member with low image score among kin, or D.disinhib"), 0, 0.3, "none", ["the family's hypocrisies"], ["family"], ["disappoint", "return", "borrow"], ["redemption", "homecoming", "feud_in_family", "addiction_recovery"], "has kin in settlement", lean="C-, D.disinhib")
role(A, "lodger", "Lodger / boarder", "ascribed", P(8), 1, 0.1, "working", ["the host family's private life"], ["host household"], ["rent", "keep to self"], ["stranger_arrives", "found_family", "keeping_a_secret"], "adult renting a room in another household", station="common among contract workers")

# -- B. work: middle America (achieved) -----------------------------------------------------------
B = "B work (middle-American occupations)"
role(B, "home_health_aide", "Home health / personal care aide", "achieved", P(11.9), 1, 0.15, "working", ["clients' health and family life", "who is lonely"], ["clients", "their families", "nurse"], ["care", "visit", "bathe", "listen"], ["caring_for_elder", "small_kindness", "keeping_a_secret"], "adult", lean="A+", strain="low pay, emotional labour", sources="BLS OEWS 2024: 3.99 M", est=False)
role(B, "retail_clerk", "Retail salesperson", "achieved", P(11.3), 1, 0.2, "working", ["who buys what", "regulars' moods"], ["customers", "manager"], ["sell", "stock", "chat"], ["anecdote", "rumour_run_wild"], "age 16+", sources="BLS OEWS 2024: 3.80 M", est=False)
role(B, "counter_worker", "Fast food / counter worker", "achieved", P(11.3), 1, 0.1, "working", ["who comes in when"], ["customers", "shift manager"], ["serve", "clean"], ["coming_of_age", "anecdote"], "age 16+", sources="BLS OEWS 2024: 3.78 M", est=False)
role(B, "manager", "General / operations manager", "achieved", P(10.7), 4, 0.4, "business", ["the business's health", "who is about to be laid off"], ["workers", "owners", "suppliers"], ["direct", "hire", "fire"], ["rivalry_superior_inferior", "ambition", "hard_choice", "revolt"], "adult 25+", lean="C+, agency+", sources="BLS OEWS 2024: 3.58 M", est=False)
role(B, "nurse", "Registered nurse", "achieved", P(9.8), 4, 0.35, "business", ["who is sick, pregnant, injured, dying"], ["patients", "doctor", "aides", "families"], ["treat", "comfort", "chart"], ["crisis_and_recovery", "grief", "keeping_a_secret", "rescue"], "adult 22+", lean="A+, C+", strain="shift work + family", station="also trained for decompression and radiation injury", sources="BLS OEWS 2024: 3.28 M", est=False)
role(B, "cashier", "Cashier", "achieved", P(9.4), 1, 0.2, "working", ["who is short of money"], ["customers"], ["ring up", "chat"], ["anecdote", "small_kindness"], "age 16+", sources="BLS OEWS 2024: 3.15 M", est=False)
role(B, "laborer", "Laborer / mover", "achieved", P(8.9), 1, 0.05, "working", ["what is being moved where"], ["crew boss"], ["haul", "load"], ["underdog", "test_of_friendship"], "adult", sources="BLS OEWS 2024: 2.98 M", est=False)
role(B, "stocker", "Stocker / order filler", "achieved", P(8.3), 1, 0.05, "working", ["shortages before anyone else"], ["manager"], ["stock", "count"], ["community_crisis", "anecdote"], "age 16+", station="sees rationing coming first", sources="BLS OEWS 2024: 2.78 M", est=False)
role(B, "customer_service", "Customer service rep", "achieved", P(8.1), 1, 0.05, "working", ["complaints", "account details"], ["callers"], ["answer", "placate"], ["negotiation"], "adult", sources="BLS OEWS 2024: 2.73 M", est=False)
role(B, "office_clerk", "Office clerk", "achieved", P(7.5), 2, 0.1, "working", ["records, who owes what"], ["office staff", "public"], ["file", "process"], ["keeping_a_secret", "enigma"], "adult", sources="BLS OEWS 2024: 2.51 M", est=False)
role(B, "janitor", "Janitor / cleaner", "achieved", P(6.6), 1, 0.1, "working", ["what is thrown away", "who stays late"], ["building users"], ["clean", "notice"], ["enigma", "keeping_a_secret", "town_character"], "adult", lean="unseen observer")
role(B, "truck_driver", "Driver (freight / delivery)", "achieved", P(9.0), 2, 0.25, "working", ["news from other settlements"], ["dispatch", "shops"], ["haul", "deliver", "carry news"], ["voyage_and_return", "letters", "rumour_run_wild"], "adult 21+", station="spine and rim haulers: the bridges between settlements (weak ties)", sources="Granovetter; existing table (driver)")
role(B, "waiter", "Waiter / server", "achieved", P(6.6), 1, 0.2, "working", ["who dines with whom", "overheard talk"], ["customers", "cook"], ["serve", "overhear"], ["courtship", "keeping_a_secret", "anecdote"], "age 16+")
role(B, "cook", "Cook", "achieved", P(4.2), 2, 0.4, "working", ["everyone's tastes and moods"], ["diners", "suppliers"], ["cook", "feed", "comfort"], ["craft_pride", "festival", "small_kindness"], "adult", lean="communion+", station="the canteen cook is a morale role (Stuster: communal meals)", sources="Stuster 1996")
role(B, "bartender", "Bartender", "achieved", P(1.9), 2, 0.7, "working", ["what people say when drunk", "who is feuding, who is courting"], ["regulars", "owner"], ["serve", "listen", "cut off", "keep peace"], ["rumour_run_wild", "keeping_a_secret", "addiction_recovery", "feud"], "adult 21+", lean="E+, A+", station="the settlement bar: a third place, and the 'Bar' clique (Palinkas)", sources="Oldenburg 1989; Palinkas 2000")
role(B, "teacher", "Teacher", "achieved", P(7.2), 4, 0.6, "business", ["which families are struggling", "children's secrets"], ["pupils", "parents", "principal"], ["teach", "counsel", "report"], ["mentorship", "coming_of_age", "festival", "rescue"], "adult 23+", lean="A+, O+", strain="parents vs school", station="teaches born-here children about Earth they have never seen", sources="Spoon River (Emily Sparks); BLS est. 2.4 M K-12")
role(B, "teacher_aide", "Teaching assistant", "achieved", P(3.6), 2, 0.1, "working", ["children's home lives"], ["pupils", "teacher"], ["help", "supervise"], ["small_kindness", "mentorship"], "adult")
role(B, "childcare_worker", "Childcare worker", "achieved", P(1.5), 2, 0.4, "working", ["every young family's routine"], ["children", "parents"], ["care", "broker"], ["found_family", "friendship", "new_life"], "adult", lean="A+", sources="Small 2009 (childcare centres broker ties)")
role(B, "librarian", "Librarian", "achieved", P(0.4), 3, 0.4, "business", ["what people are reading about (and worried about)"], ["patrons", "school"], ["lend", "guide", "host"], ["curiosity", "identity_revealed", "mentorship"], "adult", lean="O+, C+", station="also keeper of the station archive and Earth media", sources="Klinenberg 2018")
role(B, "physician", "Doctor", "achieved", P(2.4), 5, 0.8, "business", ["everyone's health, births, deaths, addictions"], ["patients", "nurses", "families"], ["diagnose", "treat", "certify death", "keep confidence"], ["crisis_and_recovery", "keeping_a_secret", "hard_choice", "grief"], "adult 28+", lean="C+", strain="one doctor for a whole settlement (overload)", station="station doctor: also coroner and flight surgeon", sources="NORC: surgeon 76")
role(B, "pharmacist", "Pharmacist", "achieved", P(1.0), 4, 0.3, "business", ["who takes what"], ["patients", "doctor"], ["dispense", "advise"], ["addiction_recovery", "keeping_a_secret"], "adult 25+", sources="NORC: pharmacist 67")
role(B, "emt", "EMT / paramedic", "achieved", P(0.8), 3, 0.4, "working", ["accidents, overdoses, domestic calls"], ["patients", "fire", "police"], ["rescue", "treat"], ["rescue", "community_crisis"], "adult 18+", station="also decompression response")
role(B, "therapist", "Counsellor / therapist", "achieved", P(1.2), 4, 0.2, "business", ["people's inner lives (confidential)"], ["clients"], ["listen", "counsel"], ["crisis_and_recovery", "remorse", "grief"], "adult", lean="A+, O+", station="station psychologist: winter-over-style isolation care (Palinkas)")
role(B, "social_worker", "Social worker", "achieved", P(2.1), 3, 0.3, "business", ["families in trouble"], ["families", "courts", "schools"], ["visit", "assess", "intervene"], ["abandonment", "hard_choice", "found_family"], "adult")
role(B, "clergy", "Pastor / clergy", "achieved", P(0.7), 4, 0.8, "business", ["confessions, marriages, who has lost faith"], ["congregation", "families"], ["preach", "counsel", "marry", "bury"], ["remorse", "forgiveness", "grief", "reformer", "festival"], "adult 28+", lean="A+", strain="confidences vs community", sources="Spoon River (Rev. Abner Peet); Gallup: 3 in 10 attend regularly")
role(B, "police", "Police officer / deputy", "achieved", P(2.0), 3, 0.7, "working", ["crimes, complaints, who has a record"], ["public", "courts", "suspects"], ["patrol", "arrest", "question"], ["pursuit", "enigma", "erroneous_judgment", "hard_choice"], "adult 21+", lean="C+, agency+", station="station marshal service (McMurdo: US Marshal)", sources="NORC: policeman 60")
role(B, "firefighter", "Firefighter", "achieved", P(1.0), 3, 0.5, "working", ["hazards in every building"], ["public", "EMT"], ["rescue", "inspect", "drill"], ["rescue", "community_crisis", "sacrifice_for_ideal"], "adult 18+", station="fire in a closed habitat is the gravest emergency: fire crews are also atmosphere crews")
role(B, "security_guard", "Security guard", "achieved", P(3.3), 1, 0.1, "working", ["who comes and goes at night"], ["employer", "public"], ["watch", "check"], ["enigma", "keeping_a_secret"], "adult 18+")
role(B, "lawyer", "Lawyer", "achieved", P(2.2), 4, 0.5, "business", ["wills, disputes, divorces"], ["clients", "judge"], ["advise", "argue"], ["supplication", "negotiation", "identity_revealed"], "adult 25+", sources="NORC: lawyer 64")
role(B, "judge", "Judge / magistrate", "achieved", S(1), 5, 0.8, "business", ["the town's disputes"], ["litigants", "police", "lawyers"], ["judge", "sentence"], ["supplication", "erroneous_judgment", "vengeance"], "adult 40+", lean="C+", sources="Spoon River (Judge Somers, the Circuit Judge); NORC 69")
role(B, "banker", "Banker / loan officer", "achieved", P(1.9), 4, 0.8, "business", ["who is in debt, who is rich"], ["borrowers", "businesses"], ["lend", "foreclose"], ["downfall", "rags_to_riches", "hard_choice", "ambition"], "adult 25+", strain="lending to friends", sources="Spoon River (Thomas Rhodes, the most-discussed); NORC 61")
role(B, "accountant", "Accountant / bookkeeper", "achieved", P(8.7), 3, 0.2, "business", ["the real state of every business"], ["clients"], ["audit", "reckon"], ["enigma", "keeping_a_secret", "downfall"], "adult", sources="NORC 57")
role(B, "shopkeeper", "Shop owner", "achieved", P(3.0), 3, 0.7, "business", ["everyone's credit", "street gossip"], ["customers", "suppliers", "neighbours"], ["sell", "extend credit", "watch the street"], ["rivalry", "small_kindness", "rags_to_riches", "anecdote"], "adult 25+", lean="E+", station="the settlement store: rationing and credit", sources="Jacobs (public characters); existing table")
role(B, "real_estate_agent", "Housing agent", "achieved", P(1.0), 3, 0.4, "business", ["who is moving, who is selling, why"], ["buyers", "sellers"], ["sell", "match"], ["stranger_arrives", "ambition"], "adult", station="housing allocation officer (space is scarce)")
role(B, "insurance_agent", "Insurance agent", "achieved", P(1.4), 3, 0.2, "business", ["who fears what"], ["clients"], ["sell", "assess claims"], ["enigma", "temptation"], "adult")
role(B, "barber", "Barber / hairdresser", "achieved", P(1.2), 2, 0.6, "working", ["what people say in the chair"], ["regulars"], ["cut", "listen", "talk"], ["rumour_run_wild", "anecdote", "keeping_a_secret"], "adult", lean="E+", sources="Oldenburg (third place hosts)")
role(B, "mechanic", "Mechanic", "achieved", P(2.1), 2, 0.3, "working", ["whose vehicle is where", "who can't pay"], ["customers"], ["repair", "diagnose"], ["craft_pride", "negotiation", "fatal_imprudence"], "adult", station="rover and tram mechanic; often also the air-plant backup")
role(B, "electrician", "Electrician", "achieved", P(2.4), 2, 0.2, "working", ["the state of every building's wiring"], ["clients", "builders"], ["wire", "repair"], ["craft_pride", "fatal_imprudence"], "adult")
role(B, "plumber", "Plumber", "achieved", P(1.5), 2, 0.2, "working", ["everyone's leaks"], ["clients"], ["repair"], ["anecdote", "craft_pride"], "adult", station="water reclamation connections")
role(B, "carpenter", "Carpenter / builder", "achieved", P(5.0), 2, 0.2, "working", ["who is building what"], ["clients", "crew"], ["build", "repair"], ["craft_pride", "daring_enterprise"], "adult", sources="existing table (builder)")
role(B, "maintenance_worker", "Maintenance worker", "achieved", P(4.5), 2, 0.15, "working", ["every building's weak points"], ["building owners"], ["fix", "inspect"], ["fatal_imprudence", "craft_pride"], "adult")
role(B, "factory_worker", "Factory hand / machinist", "achieved", P(8.0), 2, 0.1, "working", ["the plant's safety shortcuts"], ["foreman", "crew"], ["make", "operate"], ["revolt", "underdog", "fatal_imprudence"], "adult", station="export manufacturing (SP-413: 61% of workforce produces for export)", sources="SP-413")
role(B, "farmer", "Farmer", "achieved", P(2.7), 3, 0.4, "working", ["weather, soil, the harvest"], ["farmhands", "buyers"], ["plant", "harvest", "sell"], ["community_crisis", "craft_pride", "hard_choice"], "adult", station="agricultural ring farmers: food security is life support", sources="existing table")
role(B, "farmhand", "Farmhand", "achieved", P(2.0), 1, 0.05, "working", ["the farm's troubles"], ["farmer"], ["labour"], ["underdog", "courtship"], "age 16+")
role(B, "postal_worker", "Postal carrier", "achieved", P(1.0), 2, 0.6, "working", ["everyone's address, who gets letters, who doesn't"], ["every household"], ["deliver", "notice"], ["letters", "rumour_run_wild", "small_kindness"], "adult", lean="E+", station="also the Earth-mail runner", sources="existing table")
role(B, "dispatcher", "Dispatcher", "achieved", P(0.9), 2, 0.2, "working", ["every emergency call"], ["crews", "callers"], ["dispatch", "coordinate"], ["rescue", "community_crisis"], "adult")
role(B, "journalist", "Newspaper editor / reporter", "achieved", S(1), 4, 0.9, "business", ["everything the town wants known -- and hidden"], ["sources", "officials"], ["report", "publish", "investigate"], ["rumour_run_wild", "downfall", "clearing_a_name", "enigma"], "adult", lean="O+, E+", station="the settlement bulletin: the public channel's human face", sources="Spoon River (Editor Whedon); Katz & Lazarsfeld")
role(B, "musician", "Musician / entertainer", "achieved", P(0.5), 2, 0.5, "none", ["the crowd's mood"], ["audiences", "venues"], ["perform"], ["festival", "courtship", "wonder"], "adult", lean="O+, E+")
role(B, "artist", "Artist / craftsperson", "achieved", P(0.6), 2, 0.3, "none", [], ["patrons"], ["make", "show"], ["craft_pride", "wonder", "town_character"], "adult", lean="O+")
role(B, "it_tech", "IT / systems technician", "achieved", P(5.1), 3, 0.2, "business", ["everyone's messages (in principle)"], ["users"], ["fix", "configure"], ["keeping_a_secret", "enigma", "temptation"], "adult", station="station network and Earth-link", sources="BLS est. (software/IT)")
role(B, "engineer", "Engineer", "achieved", P(3.0), 4, 0.3, "business", ["how things really work and fail"], ["crews", "management"], ["design", "certify"], ["daring_enterprise", "fatal_imprudence", "hard_choice"], "adult 22+", sources="NORC 67")
role(B, "scientist", "Scientist", "achieved", P(1.5), 4, 0.3, "business", ["data others don't have"], ["lab", "funders"], ["study", "measure", "publish"], ["enigma", "reformer", "curiosity"], "adult 24+", station="the 'beakers': a class apart from support staff (McMurdo)", sources="Palinkas; McMurdo")
role(B, "unemployed", "Unemployed", "achieved", P(12.0), 0, 0.15, "working", [], ["family"], ["seek work", "idle"], ["underdog", "rags_to_riches", "temptation", "addiction_recovery"], "adult 18-64", strain="identity loss (breadwinner)", sources="existing table")

# -- C. station-specific occupations -----------------------------------------------------------------
C = "C station roles (essential systems and station life)"
role(C, "air_plant_operator", "Air plant operator", "achieved", P(1.5), 4, 0.5, "working", ["the true state of the air"], ["shift crew", "administration"], ["monitor", "repair", "ration"], ["community_crisis", "fatal_imprudence", "hard_choice", "sacrifice_for_ideal"], "adult", lean="C+", strain="understaffed; blamed first", station="station-only", sources="SP-413 life support; Stuster")
role(C, "water_tech", "Water reclamation technician", "achieved", P(1.0), 3, 0.3, "working", ["the water reserves"], ["crew"], ["filter", "test"], ["community_crisis", "fatal_imprudence"], "adult", station="station-only")
role(C, "power_tech", "Power / grid technician", "achieved", P(1.0), 3, 0.3, "working", ["which sections run short"], ["crew", "administration"], ["maintain", "reroute"], ["community_crisis", "daring_enterprise"], "adult", station="station-only")
role(C, "agronomist", "Agronomist / hydroponics keeper", "achieved", P(2.5), 4, 0.4, "business", ["the food stocks and blights"], ["farmers", "administration"], ["grow", "breed", "warn"], ["community_crisis", "craft_pride", "enigma"], "adult", station="station-only; seed bank keeper is a sub-role")
role(C, "hull_inspector", "Hull and structure inspector", "achieved", P(0.5), 4, 0.3, "business", ["every crack in the world"], ["engineers", "administration"], ["inspect", "report", "seal"], ["fatal_imprudence", "hard_choice", "keeping_a_secret"], "adult", strain="reporting a flaw that closes a neighbourhood", station="station-only")
role(C, "radiation_officer", "Radiation safety officer", "achieved", P(0.2), 4, 0.3, "business", ["exposures, storm warnings"], ["everyone during storms"], ["measure", "shelter", "warn"], ["community_crisis", "overcoming_menace"], "adult", station="station-only")
role(C, "eva_tech", "EVA technician", "achieved", P(0.5), 4, 0.5, "working", ["the outside"], ["EVA partner", "control"], ["go outside", "repair", "rescue"], ["daring_enterprise", "rescue", "wonder", "voyage_and_return"], "adult 21+", lean="courage+, C+", station="station-only; sees the view daily (overview effect)")
role(C, "port_master", "Port / docking master", "achieved", P(0.3), 4, 0.6, "business", ["who and what arrives and leaves"], ["pilots", "customs", "cargo"], ["schedule", "clear", "refuse"], ["stranger_arrives", "pursuit", "homecoming"], "adult", station="station-only")
role(C, "traffic_controller", "Spine traffic controller", "achieved", P(0.3), 3, 0.2, "business", ["every movement along the spine"], ["pilots", "drivers"], ["route", "hold"], ["rescue", "enigma"], "adult", station="station-only")
role(C, "shuttle_pilot", "Shuttle pilot", "achieved", P(0.3), 5, 0.6, "business", ["Earth and other stations"], ["port", "passengers"], ["fly", "carry"], ["voyage_and_return", "homecoming", "letters", "courtship"], "adult 25+", station="station-only", sources="NORC: airline pilot 69, astronaut 72")
role(C, "cargo_handler", "Cargo handler", "achieved", P(1.5), 1, 0.2, "working", ["what came in on each ship (and what went missing)"], ["port", "stores"], ["load", "count"], ["enigma", "temptation", "anecdote"], "adult", station="station-only")
role(C, "recycler", "Recycler / waste processor", "achieved", P(2.0), 1, 0.1, "working", ["what everyone throws away"], ["crew"], ["sort", "process"], ["enigma", "town_character", "underdog"], "adult", station="station-only; nothing leaves the loop")
role(C, "comms_officer", "Earth-link communications officer", "achieved", P(0.3), 3, 0.5, "business", ["every message to and from Earth"], ["everyone with family on Earth"], ["relay", "schedule"], ["letters", "earthsick", "keeping_a_secret", "grief"], "adult", station="station-only; brings news of deaths on Earth")
role(C, "administrator", "Station administrator / council", "achieved", S(3), 5, 0.9, "business", ["budgets, rations, the real risks"], ["council", "systems chiefs", "public"], ["decide", "ration", "announce"], ["revolt", "scapegoat", "hard_choice", "election", "community_crisis"], "adult 30+", strain="blamed for everything (displacement)", station="the 'mission control' of the settlement: the target of displaced tension", sources="Kanas; Mars-500; SP-413")
role(C, "marshal", "Station marshal", "achieved", S(1), 4, 0.8, "working", ["crimes, disputes, the quarantine list"], ["public", "administrator", "judge"], ["patrol", "arrest", "mediate"], ["pursuit", "erroneous_judgment", "feud", "supplication"], "adult 25+", station="McMurdo: law enforcement by a US Marshal", sources="McMurdo")
role(C, "ombudsman", "Ombudsman", "achieved", S(0.3), 4, 0.5, "business", ["grievances against the administration"], ["residents", "administration"], ["hear", "mediate"], ["supplication", "clearing_a_name", "revolt"], "adult 35+", lean="A+, H+", station="station-only")
role(C, "quarantine_officer", "Customs and quarantine officer", "achieved", P(0.2), 3, 0.4, "business", ["who brought what aboard"], ["arrivals", "port"], ["inspect", "hold", "release"], ["stranger_arrives", "hard_choice", "enigma"], "adult", station="station-only")
role(C, "arrival_coordinator", "Arrival coordinator", "achieved", S(0.5), 3, 0.5, "business", ["every newcomer's story"], ["newcomers", "housing"], ["welcome", "place", "orient"], ["stranger_arrives", "found_family", "friendship"], "adult", lean="communion+", station="station-only: the first friend of the player")
role(C, "archivist", "Station archivist / historian", "achieved", S(0.2), 3, 0.3, "business", ["the station's history and its buried parts"], ["council", "researchers"], ["record", "preserve", "tell"], ["identity_revealed", "enigma", "curiosity"], "adult", lean="O+, C+", station="station-only")
role(C, "contract_worker", "Contract worker", "achieved", P(40), 1, 0.1, "working", ["the job site"], ["crew boss", "other contractors"], ["work a term", "save", "leave"], ["stranger_arrives", "earthsick", "temptation", "courtship"], "adult 21-55", strain="temporary, less committed (shimanagashi)", station="SP-413 construction workforce; McMurdo contractors", sources="SP-413; McMurdo")

# -- D. civic and institutional (achieved, mostly unpaid) -------------------------------------------
D = "D civic and institutional"
for rid, name, per, pr, prom, knows, dut, hooks, elig, note in [
    ("mayor", "Mayor / settlement chair", 1, 5, 0.95, ["the settlement's politics"], ["preside", "promise", "represent"], ["election", "revolt", "downfall", "scapegoat"], "adult 30+", "NORC: mayor of a large city 72"),
    ("council_member", "Council member", 5, 4, 0.7, ["deals, budgets"], ["vote", "debate"], ["election", "negotiation", "ambition"], "adult 25+", ""),
    ("school_board", "School board member", 5, 3, 0.4, ["the school's troubles"], ["vote", "hire"], ["reformer", "election"], "adult parent", ""),
    ("pta_head", "PTA / parents' association head", 1, 2, 0.5, ["every family with children"], ["organise", "fundraise"], ["festival", "rivalry", "election"], "parent", "Small 2009"),
    ("church_elder", "Church elder / deacon", 4, 3, 0.5, ["the congregation's troubles"], ["lead", "judge", "help"], ["reformer", "forgiveness", "remorse"], "adult 40+, congregant", ""),
    ("choir_director", "Choir / music director", 1, 2, 0.4, [], ["rehearse", "perform"], ["festival", "courtship"], "adult", ""),
    ("coach", "Youth sports coach", 4, 3, 0.6, ["the kids and their parents"], ["train", "pick teams", "inspire"], ["underdog", "mentorship", "coming_of_age"], "adult", ""),
    ("scout_leader", "Scout / youth club leader", 2, 2, 0.4, ["the children's characters"], ["lead", "teach"], ["coming_of_age", "mentorship", "quest"], "adult", ""),
    ("volunteer_firefighter", "Volunteer firefighter", 10, 3, 0.4, ["hazards"], ["drill", "respond"], ["rescue", "community_crisis"], "adult 18+", "AmeriCorps: 28% formal volunteers"),
    ("block_captain", "Block captain / HOA president", 2, 2, 0.6, ["every complaint on the street"], ["enforce", "organise", "complain"], ["rivalry", "feud", "reformer"], "homeowner adult", ""),
    ("watch_captain", "Neighbourhood watch captain", 1, 2, 0.5, ["who is out at night"], ["patrol", "report"], ["erroneous_judgment", "scapegoat", "enigma"], "adult", "Jacobs (eyes on the street)"),
    ("union_steward", "Union steward", 2, 3, 0.5, ["grievances at work"], ["represent", "negotiate", "strike"], ["revolt", "negotiation", "rivalry_superior_inferior"], "worker", ""),
    ("festival_organiser", "Festival organiser", 1, 2, 0.6, ["everyone's talents"], ["plan", "rally"], ["festival", "daring_enterprise"], "adult, E+", ""),
    ("club_president", "Club / lodge president", 3, 2, 0.4, ["members' business"], ["preside", "host"], ["election", "rivalry"], "adult", "Putnam 2000"),
    ("veterans_leader", "Veterans' / old hands' association", 1, 3, 0.4, ["old stories"], ["remember", "honour"], ["grief", "identity_revealed"], "veteran or founder", ""),
    ("library_board", "Library / archive board", 3, 3, 0.3, [], ["fund", "choose"], ["reformer"], "adult", "Klinenberg"),
    ("safety_committee", "Habitat safety committee", 5, 4, 0.5, ["near-misses"], ["inspect", "drill", "report"], ["fatal_imprudence", "hard_choice", "reformer"], "adult", "station-only; W.tight"),
]:
    role(D, rid, name, "achieved", S(per), pr, prom, "none", knows, ["settlement residents"], dut, hooks, elig, sources=note)

# -- E. informal community roles (emergent: computed from traits + network position) ----------------
E = "E informal community roles (emergent)"
for rid, name, rule, prom, knows, dut, hooks, lean, src in [
    ("public_character", "Public character", "high degree across many foci + E high + a street-facing job or porch", 0.8, ["everyone's comings and goings"], ["watch", "greet", "relay"], ["rumour_run_wild", "town_character", "rescue"], "E+", "Jacobs 1961; Duneier 1999"),
    ("regular", "The regular", "visits a third place near-daily", 0.4, ["the third place's talk"], ["sit", "talk"], ["anecdote", "friendship"], "E+", "Oldenburg 1989"),
    ("opinion_leader", "Opinion leader", "high degree + attends to news (O+) + trusted (H+)", 0.8, ["the news first"], ["interpret", "persuade"], ["rumour_run_wild", "election", "clearing_a_name"], "O+, E+, H+", "Katz & Lazarsfeld 1955"),
    ("broker", "Broker (bridge between groups)", "ties into 2+ otherwise separate clusters (structural hole)", 0.6, ["both sides' news"], ["connect", "translate", "withhold"], ["alliance_of_necessity", "divided_loyalty", "negotiation"], "E+", "Burt 1992"),
    ("gatekeeper", "Gatekeeper", "controls access to a place, group or resource (role + low A.trust)", 0.5, ["who is in and who is out"], ["admit", "refuse", "vet"], ["stranger_arrives", "obstacles_to_love"], "C+, trust-", "Lewin; story 03"),
    ("gossip", "Gossip hub", "K.gossip very high + high degree", 0.7, ["everything, distorted"], ["tell", "embellish"], ["rumour_run_wild", "mistaken_jealousy", "keeping_a_secret"], "E+, K.gossip+", "Dunbar 2004"),
    ("busybody", "Busybody", "K.gossip high + C high + A low", 0.5, ["the street's rule-breaking"], ["watch", "report", "complain"], ["erroneous_judgment", "scapegoat"], "C+, A-", "Jacobs; Spoon River"),
    ("helper", "Neighbourhood helper", "A high + communion high (informal helping)", 0.3, ["who needs what"], ["help", "lend", "visit"], ["small_kindness", "found_family", "caring_for_elder"], "A+", "AmeriCorps 2023: 54% help neighbours"),
    ("fixer", "The fixer ('knows a guy')", "broker position + low H or high agency", 0.5, ["who can get what"], ["arrange", "trade favours"], ["temptation", "negotiation", "enigma"], "agency+, H-", "Burt"),
    ("elder_storyteller", "Elder storyteller / local historian", "age 70+ + long residence (founder) + E or O high", 0.5, ["the settlement's past"], ["tell", "remember"], ["identity_revealed", "curiosity", "grief"], "O+", "Johnson (storytellers)"),
    ("town_character", "Town character (eccentric)", "an extreme facet or D.psych mild + visibility", 0.6, ["odd truths"], ["wander", "declaim"], ["town_character", "curiosity", "scapegoat"], "O+, extreme facet", "Winesburg (grotesques)"),
    ("town_drunk", "Town drunk", "S.coping drink + visibility", 0.6, ["the bar's secrets"], ["drink", "ramble"], ["addiction_recovery", "redemption", "town_character"], "D.disinhib", "Spoon River (Chase Henry)"),
    ("newcomer", "Newcomer / outsider", "C.origin recent_arrival or new in settlement (the player starts here)", 0.5, [], ["ask", "learn"], ["stranger_arrives", "scapegoat", "found_family"], "", "psychology 03; Kanas"),
    ("loner", "Loner / isolate", "few ties + detachment or avoidance", 0.2, [], ["keep apart"], ["friendship", "estrangement", "enigma"], "E-, att_avoid+", "Palinkas (periphery)"),
    ("scapegoat", "Scapegoat", "outgroup + low image score under settlement stress", 0.6, [], ["endure"], ["scapegoat", "clearing_a_name"], "", "Kanas; story 03"),
    ("leader_task", "Task (instrumental) leader", "agency + C + competence, recognised by consensus", 0.8, ["what must be done"], ["organise", "decide"], ["daring_enterprise", "community_crisis", "hard_choice"], "agency+, C+", "Bales; Johnson et al. 2003"),
    ("leader_heart", "Heart (expressive) leader", "communion + A + centrality, recognised by consensus", 0.7, ["how people are really doing"], ["console", "rally", "include"], ["found_family", "forgiveness", "grief"], "communion+, A+", "Johnson et al. 2003 (expressive leadership)"),
    ("clown", "Clown / joker", "humour high + E high + ties across groups", 0.7, ["what everyone is tense about"], ["joke", "defuse", "bridge"], ["anecdote", "alliance_of_necessity", "town_character"], "humour+, E+", "Johnson (the clown was the most central figure)"),
    ("peacemaker", "Peacemaker", "A high + H high + trusted by both sides of a conflict", 0.5, ["both sides of quarrels"], ["mediate", "calm"], ["forgiveness", "feud", "divided_loyalty"], "A+, H+", "Johnson"),
    ("confidant", "Counsellor / confidant", "A high + discretion (K.gossip low) + trusted", 0.4, ["other people's troubles (kept)"], ["listen", "advise"], ["crisis_and_recovery", "remorse", "keeping_a_secret"], "A+, gossip-", "Johnson (counsellors); Palinkas (support paradox)"),
    ("buddy", "Buddy", "a reciprocal close tie (layer 5) at work", 0.2, ["one friend's everything"], ["cover for", "share"], ["test_of_friendship", "betrayal", "friendship"], "", "Johnson (buddies)"),
    ("rival", "Standing rival", "a long negative tie with a peer (same focus)", 0.4, ["the other's weaknesses"], ["compete", "needle"], ["rivalry", "alliance_of_necessity"], "A-", "story 03"),
    ("matchmaker", "Matchmaker", "high communion + gossip + interest in others' lives", 0.4, ["who likes whom"], ["introduce", "arrange"], ["courtship", "love_triangle"], "E+, A+", "ATU realistic tales"),
]:
    role(E, rid, name, "emergent", RULE(rule), 0, prom, "none", knows, ["whoever the network puts them beside"], dut, hooks, "computed", lean=lean, sources=src)

# -- F. life stage and station status ------------------------------------------------------------------
F = "F life stage and station status"
for rid, name, freq, pr, prom, hooks, elig, station, src, est in [
    ("student", "Student", P(160), 0, 0.05, ["coming_of_age", "rivalry", "courtship"], "age 6-18", "", "existing table", True),
    ("university_student", "University / trade student", P(8), 1, 0.05, ["mentorship", "courtship", "voyage_and_return"], "age 18-26", "", "existing table", True),
    ("retiree", "Retiree", P(140), 1, 0.2, ["caring_for_elder", "town_character", "grief"], "age 62+", "", "existing table", True),
    ("preschooler", "Young child (under school age)", P(60), 0, 0.02, ["new_life", "lost_and_found"], "age 0-5", "", "existing table", True),
    ("veteran", "Veteran", P(20), 3, 0.3, ["grief", "identity_revealed", "sacrifice_for_ideal"], "adult who served", "veterans of station emergencies count", "", True),
    ("disabled", "Living with disability", P(80), 0, 0.15, ["changed", "underdog"], "any age", "low gravity sections change mobility", "", True),
    ("founder", "Founding settler", RULE("arrived at the settlement's founding (W.age)"), 3, 0.6, ["identity_revealed", "downfall", "town_character"], "C.origin first_gen and early", "the founders' generation holds civic roles early and long (Gans)", "Gans 1967; SP-413", False),
    ("born_here", "Born on the station", RULE("C.origin born_here"), 1, 0.05, ["coming_of_age", "earthsick", "wonder"], "any age", "has never seen Earth", "psychology 03", False),
    ("recent_arrival", "Recent arrival", RULE("C.origin recent_arrival"), 1, 0.3, ["stranger_arrives", "earthsick", "found_family"], "any age", "the player's peers", "psychology 03", False),
]:
    role(F, rid, name, "ascribed", freq, pr, prom, "none", [], [], [], hooks, elig, station=station, sources=src, est=est)


def main():
    bad = [(r["id"], h) for r in R for h in r["hooks"] if h not in STORY_IDS]
    ids = [r["id"] for r in R]
    assert len(ids) == len(set(ids)), "duplicate role id"
    root = ROOT
    out = {"_about": "Role catalogue for the story engine (research/roles/05_roles_in_the_engine.md). Generated by "
                     "tools/story/make_roles.py. freq: per1000 residents | per_settlement | rule (emergent roles, computed "
                     "from tokens and network position). prestige 1-5; prominence 0-1 = salience of this person's acts "
                     "in propagation; knows = privileged knowledge channels; set = role set (adds ties); duties = event "
                     "verbs; hooks = story_types.json ids.", "version": 1, "roles": R}
    with open(os.path.join(root, "research", "roles", "roles.json"), "w") as f:
        json.dump(out, f, indent=1)
    fams = []
    for r in R:
        if r["family"] not in fams:
            fams.append(r["family"])
    md = ["# 4. The role catalogue", "",
          "Generated by `tools/story/make_roles.py`, with the same data as `roles.json`. **%d roles** in %d families. Every story hook is checked against the story catalogue (%s)." % (
              len(R), len(fams), "all valid" if not bad else "INVALID: %s" % bad), "",
          "Columns: frequency (per 1,000 residents, per settlement, or the rule that makes the role emerge) · prestige 1–5 · prominence 0–1 (how far this person's acts spread) · what the role knows without being told · story hooks. Frequencies marked * are estimates at BLS magnitudes; the rest are sourced.", ""]
    for fam in fams:
        md += ["## " + fam[0] + ". " + fam[2:].capitalize(), "", "| role | freq | prestige | prom. | knows | hooks | station |", "|---|---|---|---|---|---|---|"]
        for r in R:
            if r["family"] != fam:
                continue
            fq = r["freq"]
            fs = ("%.1f/1k" % fq["per1000"]) if "per1000" in fq else ("%s/settlement" % fq["per_settlement"]) if "per_settlement" in fq else fq["rule"]
            if r["estimate"] and "per1000" in fq:
                fs += "*"
            md.append("| **%s** `%s` | %s | %s | %.1f | %s | %s | %s |" % (
                r["name"], r["id"], fs, r["prestige"], r["prominence"], "; ".join(r["knows"]), ", ".join(r["hooks"]), r["station"]))
        md.append("")
    with open(os.path.join(root, "research", "roles", "04_role_catalogue.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("%d roles in %d families; invalid hooks: %s" % (len(R), len(fams), bad or "none"))


if __name__ == "__main__":
    main()
