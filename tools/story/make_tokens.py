#!/usr/bin/env python3
"""Writes research/psychology/tokens.json, the story engine's token catalogue
(research/psychology/06_story_engine_framework.md section 2). Edit the tables here, then rerun:

    python3 tools/story/make_tokens.py
"""
import json
import os

T = []
U = [0, 1]
S = [-1, 1]


def t(id, kind, rng, derive, source, stored=False, prompt="band"):
    T.append({"id": id, "kind": kind, "range": rng, "derive": derive, "source": source,
              "stored": stored, "prompt": prompt})


# identity (existing generator)
for k, kind, r, d in [
        ("ID.pid", "ref", None, "NpcHouseholds member pid"),
        ("ID.name", "text", None, "literary phase"),
        ("ID.age", "int", [0, 99], "L0 age"),
        ("ID.sex", "enum", ["female", "male"], "L0 sex"),
        ("ID.life_stage", "enum", ["child", "teen", "young_adult", "adult", "elder"], "L0 life_stage"),
        ("ID.household", "ref", None, "NpcHouseholds"),
        ("ID.settlement", "ref", None, "npc_settlements.json"),
        ("ID.occupation", "enum", None, "L0 occupation (the roles research will extend it)")]:
    t(k, kind, r, d, "existing generator", stored=True, prompt="text")

# settlement culture (03)
for k, kind, r, d, s in [
        ("W.age", "float", [0, 200], "settlement record: years since founding", "Bazzi et al. 2020 (frontier experience)"),
        ("W.indiv", "float", U, "frontier experience x voluntary settlement x low-interdependence economy", "Bazzi et al. 2020; Kitayama et al. 2006; Talhelm et al. 2014"),
        ("W.honor", "float", U, "mobile wealth x weak policing", "Nisbett & Cohen 1996"),
        ("W.tight", "float", U, "threat ecology: density, life-support risk, disasters", "Gelfand et al. 2011"),
        ("W.relmob", "float", U, "growth and turnover vs a closed interdependent economy", "Thomson, Yuki et al. 2018"),
        ("W.org", "enum", ["hierarchical", "individualistic", "heterogenistic"], "founding record", "NASA SP-413 (1975), chapter 3 appendix A"),
        ("W.legacy", "map", None, "trait-mean shifts from the founding economy", "Obschonka et al. 2018"),
        ("W.outgroup", "enum", ["administration", "rival_settlement", "newcomers", "none"], "settlement record + stress", "Kanas (Shuttle-Mir); Basner et al. 2014 (Mars-500)")]:
    t(k, kind, r, d, s, prompt="words")

# personality (01)
for k in "OCEAN":
    t("P." + k, "float", U, "stored L2 personality", "Costa & McCrae, NEO PI-R", stored=True)
t("P.H", "float", U, "stored L2 'honesty'", "Ashton & Lee, HEXACO", stored=True)
for f, d in [("anxiety", "N"), ("angry_hostility", "N"), ("vulnerability", "N"), ("impulsiveness", "N"),
             ("gregariousness", "E"), ("assertiveness", "E"), ("warmth", "stored L2 warmth"),
             ("trust", "A"), ("straightforwardness", "A"), ("altruism", "A"), ("compliance", "A"),
             ("modesty", "A"), ("dutifulness", "C"), ("deliberation", "C"), ("fantasy", "O"),
             ("sincerity", "H"), ("fairness", "H"), ("greed", "H")]:
    t("P.f." + f, "float", U, ("domain %s + hashed offset (sd 0.08)" % d) if len(d) == 1 else d, "NEO PI-R / HEXACO facets")
t("P.agency", "float", U, "0.5 assertiveness + 0.3 E + 0.2 (1 - compliance) (+ role status later)", "interpersonal circumplex (Leary; Wiggins)")
t("P.communion", "float", U, "0.5 warmth + 0.3 A + 0.2 E", "interpersonal circumplex")
t("P.style", "enum", ["assured_dominant", "arrogant_calculating", "cold_hearted", "aloof_introverted",
                      "unassured_submissive", "unassuming_ingenuous", "warm_agreeable", "gregarious_extraverted"],
  "octant of (agency, communion)", "interpersonal circumplex", prompt="word")
t("P.att_anx", "float", U, "0.6 vulnerability + noise (+ backstory)", "Bartholomew & Horowitz 1991")
t("P.att_avoid", "float", U, "0.5 (1 - warmth) + 0.3 (1 - trust) + noise", "Bartholomew & Horowitz 1991")
t("P.att", "enum", ["secure", "preoccupied", "dismissing", "fearful"], "quadrant of (anx, avoid)", "Bartholomew & Horowitz 1991", prompt="word")
t("P.if", "list", None, "3-6 hashed (situation feature -> stance modifier) pairs, trait-weighted", "Mischel & Shoda 1995 (CAPS)", prompt="matching features only")
for v in ["self_direction", "stimulation", "hedonism", "achievement", "power", "security", "conformity",
          "tradition", "benevolence", "universalism"]:
    t("V." + v, "float", U, "circular draw (direction + strength), trait and age shifts", "Schwartz, theory of basic values")
t("V.top", "list", None, "the top two values", "Schwartz", prompt="words")
for m in ["care", "fair", "loyal", "auth", "pure", "lib"]:
    t("M." + m, "float", U, "from A/warmth, H, C/tradition, O, W.indiv", "Moral Foundations Theory (Graham & Haidt)")
for k in ["E.P0", "E.A0", "E.D0"]:
    t(k, "float", S, "PAD temperament from the Big Five", "Mehrabian 1996")
for k in ["E.P", "E.A", "E.D"]:
    t(k, "float", S, "current mood: temperament + recent emotion pushes, relaxing with a half-life", "Mehrabian PAD")
for e in ["joy", "distress", "hope", "fear", "happy_for", "pity", "gloating", "resentment", "pride", "shame",
          "admiration", "reproach", "gratitude", "anger", "gratification", "remorse", "relief", "disappointment"]:
    t("F." + e, "float", U, "OCC appraisal of known events (06 section 5.1), only above threshold", "Ortony, Clore & Collins 1988; GAMYGDALA")
t("S.stress", "float", U, "value/foundation-violating events + ICE stressors, decaying", "Crusader Kings III; Palinkas & Suedfeld 2008")
t("S.coping", "enum", ["withdraw", "confide", "work", "drink", "pray", "lash_out", "ruminate"], "personality under stress", "CK3 coping; Dwarf Fortress needs", prompt="word")

# personality-disorder dimensions (02)
t("D.lpfs", "int", [0, 4], "sigmoid of trait extremity; ~12% >= 1, ~1% >= 3; stress raises it, secure attachment lowers it", "DSM-5 AMPD Criterion A; Volkert et al. 2018")
for k, d in [("D.negaff", "high-N tail"), ("D.detach", "low-E tail + avoidance"), ("D.antag", "low-A and low-H tails"),
             ("D.disinhib", "low-C tail + impulsiveness"), ("D.anank", "high-C tail + low O"),
             ("D.psych", "rare separate draw (~3%), O.fantasy link")]:
    t(k, "float", U, d, "AMPD Criterion B / ICD-11 trait qualifiers")
t("D.facets", "list", None, "2-3 strongest AMPD facets as behaviour words; NEVER diagnostic labels", "AMPD 25 facets; stigma review (JMIR Mental Health 2019)", prompt="behaviour words")

# frontier/space adaptation (03)
for k, kind, r, d, s in [
        ("C.origin", "enum", ["born_here", "first_gen", "recent_arrival", "contract"], "household history", "voluntary settlement; SP-413 selection"),
        ("C.motive", "enum", ["choice", "money", "escape", "assigned", "born"], "backstory", "SP-413 (commitment protects)"),
        ("C.fit", "float", U, "value fit to W.org and W.tight", "SP-413 matching problem"),
        ("C.isol", "float", U, "isolation tolerance from N, attachment, introversion", "Palinkas & Suedfeld 2008"),
        ("C.solip", "float", U, "artificiality exposure x grounding", "SP-413 solipsism syndrome"),
        ("C.earthsick", "float", U, "origin + O + age", "Kanas & Manzey (Earth out of view)"),
        ("C.awe", "float", U, "O + view access", "Yaden et al. 2016 (overview effect)"),
        ("C.displace", "float", U, "N x stress x outgroup", "Kanas; Mars-500")]:
    t(k, kind, r, d, s)

# ties (04)
for k, kind, r, d, s in [
        ("R.layer", "enum", [5, 15, 50, 150, 500], "focus kind + homophily", "Dunbar layers (Zhou et al. 2005)"),
        ("R.kind", "enum", ["kin", "partner", "household", "friend", "coworker", "neighbour", "classmate",
                            "congregant", "acquaintance", "rival", "authority"], "focus", "Feld 1981"),
        ("R.model", "enum", ["CS", "AR", "EM", "MP"], "focus kind", "Fiske 1992"),
        ("R.valence", "float", S, "homophily + history; deltas stored", "Wish, Deutsch & Kaplan 1976"),
        ("R.power", "float", S, "agency and role difference", "Wish et al. (equal-unequal); circumplex"),
        ("R.formal", "float", U, "focus kind", "Wish et al. (socioemotional-task)"),
        ("R.trust", "float", U, "layer, A.trust, history", "Granovetter 1973; Nowak & Sigmund 1998"),
        ("R.debt", "float", S, "Equality Matching balance of favours", "Fiske (EM)"),
        ("R.grievance", "map", None, "{avoid, revenge, benevolence} after a transgression, decaying", "McCullough (TRIM)")]:
    t(k, kind, r, d, s, stored=k in ("R.valence", "R.trust", "R.debt", "R.grievance"))

# knowledge (04, 06 section 4)
for k, kind, r, d, s in [
        ("K.event", "ref", None, "event id", "Talk of the Town (belief facets)"),
        ("K.source", "ref", None, "last teller on the earliest live path, or witness / public", "Talk of the Town (source tracing)"),
        ("K.hops", "int", [0, 3], "hops on the earliest live path", "Christakis & Fowler (3-degree horizon)"),
        ("K.when", "time", None, "arrival time on the earliest live path", "continuous-time independent cascade; Kempe et al. 2003"),
        ("K.certainty", "float", U, "1 for witnesses, x 0.9 trust(teller) per hop", "Talk of the Town (evidence strength)"),
        ("K.fields", "list", None, "fields that survived levelling (p 0.8 per hop)", "Allport & Postman 1947"),
        ("K.mag", "int", [0, 3], "magnitude after sharpening", "Allport & Postman 1947"),
        ("K.intent", "enum", ["deliberate", "careless", "accidental", "forced"], "intent after assimilation toward the hearer's prior of the actor", "Allport & Postman; Weiner"),
        ("K.lied", "bool", None, "came through a lie (engine-only; the holder doesn't know)", "Talk of the Town"),
        ("K.gossip", "float", U, "0.5 + 0.9 E - 0.3 C H", "Dunbar 2004; Talk of the Town (extraversion)"),
        ("K.embellish", "float", U, "(1 - H) + E", "Allport & Postman (sharpening)"),
        ("K.lie", "float", U, "low H x grievance or motive", "Talk of the Town; Kashy & DePaulo"),
        ("K.k_threshold", "int", [1, 3], "1 credulous (high A, N) .. 3 skeptic (high C, low A)", "Centola (complex contagion)")]:
    t(k, kind, r, d, s)

# events (06 section 3)
for k, kind, r, d in [
        ("EV.id", "int", None, "sequential"), ("EV.t", "time", None, "game minutes"),
        ("EV.place", "ref", None, "settlement + (s, x)"), ("EV.actor", "ref", None, "pid | PLAYER | GROUP"),
        ("EV.verb", "enum", None, "verb taxonomy data file (goal effects, moral tags, relational reading, salience)"),
        ("EV.patients", "list", None, "up to 3 pids"), ("EV.object", "enum", None, "tag"),
        ("EV.mag", "int", [0, 3], "trivial .. major"),
        ("EV.intent", "enum", ["deliberate", "careless", "accidental", "forced"], "from the act"),
        ("EV.vis", "enum", ["public", "private", "secret"], "from the act"),
        ("EV.claim", "ref", None, "for statements: what is asserted (lies included)")]:
    t(k, kind, r, d, "06 section 3", stored=True, prompt="rendered as a belief")

# reaction (06 section 5)
for k, kind, r, d in [
        ("X.stance", "enum", ["warm", "friendly", "neutral", "guarded", "cold", "hostile", "afraid", "ingratiating", "avoidant", "confronting"],
         "scored from opinion, fear, complementarity, CAPS, culture, D, coping"),
        ("X.intent", "enum", ["thank", "warn", "accuse", "ask_help", "share_news", "test", "sell", "keep_away", "recruit", "chat"], "stance + needs + role"),
        ("X.disclose", "list", None, "beliefs they will share: trust, gossip, self-protection"),
        ("X.tone", "enum", None, "mood + stance words"),
        ("X.opinion", "float", S, "sum of named decaying modifiers, negatives x2.5, complex-contagion gate, balance")]:
    t(k, kind, r, d, "06 section 5", stored=k == "X.opinion", prompt="words")

# story (research/story/04_arcs_in_the_engine.md section 1)
for k, kind, r, d, s_ in [
        ("ST.type", "enum", None, "one of the story types in research/story/story_types.json", "catalogue (Polti, Booker, Tobias, Propp, Regis, kishotenketsu)"),
        ("ST.family", "enum", ["bonds_forming", "bonds_tested", "bonds_broken", "harm_justice", "power_community", "self_change", "quiet"], "catalogue", "research/story/03"),
        ("ST.role", "text", None, "the role this person is cast in", "Polti's elements; Propp's spheres of action"),
        ("ST.actant", "enum", ["subject", "object", "sender", "receiver", "helper", "opponent"], "the role's actant", "Greimas"),
        ("ST.beat", "enum", None, "current beat of the arc's template", "Propp (functions); Regis; kishotenketsu"),
        ("ST.stage", "enum", ["intro", "exciting", "rise", "climax", "tragic", "fall", "suspense", "resolution"], "beat's stage", "Freytag"),
        ("ST.tension", "float", U, "beat's tension", "Freytag; Facade drama manager"),
        ("ST.value", "map", None, "value pair turned by the arc and its current polarity", "McKee"),
        ("ST.shape", "enum", ["rags_to_riches", "riches_to_rags", "man_in_a_hole", "icarus", "cinderella", "oedipus"], "target valence curve", "Reagan et al. 2016"),
        ("ST.mythos", "enum", ["comedy", "romance", "tragedy", "irony", "faded"], "outcome family, set at resolution", "Frye"),
        ("ST.theme", "text", None, "the premise the dialogue may echo, never state", "Egri"),
        ("ST.deed", "enum", ["done", "undone"], "harmful beat: done or not", "Aristotle, Poetics XIV"),
        ("ST.aware", "enum", ["knowing", "ignorant"], "harmful beat: knowingly or in ignorance", "Aristotle, Poetics XIV"),
        ("ST.affect", "enum", ["suspense", "surprise", "curiosity", "none"], "what the beat serves for the player (K asymmetry)", "Brewer & Lichtenstein"),
        ("ST.promise", "list", None, "planted setups awaiting payoff", "setup/payoff (Chekhov); Propp interdiction/violation"),
        ("ST.quality", "float", U, "stakes x closeness x causal density x recognition/reversal x fit x payoff x novelty", "research/story/02 section 2.3"),
        ("ST.featured", "bool", None, "surfaced by the drama manager (vs background)", "Facade; RimWorld storytellers"),
        ("ST.chorus", "map", None, "{hops, side, source chain} for people outside the arc", "propagation + Heider balance; Spoon River"),
        ("ST.sequel", "list", None, "follow-on arcs this arc can open", "research/story/04 section 2.8"),
        ("ST.storyteller", "enum", ["cassandra", "phoebe", "ghibli"], "pacing personality (game setting)", "RimWorld storytellers"),
        ("ST.chronicle", "list", None, "the player's history as finished arcs (stored)", "research/story/04 section 2.9")]:
    t(k, kind, r, d, s_, stored=k in ("ST.chronicle",), prompt="story card")

# roles (research/roles/05_roles_in_the_engine.md section 1)
for k, kind, r, d, s_ in [
        ("RL.primary", "enum", None, "main work role (research/roles/roles.json id)", "BLS OEWS 2024; SP-413"),
        ("RL.household", "list", None, "household and kin roles (parent, caregiver, kinkeeper...)", "households; di Leonardo 1987; AARP 2025"),
        ("RL.civic", "list", None, "civic/institutional roles held (joiners hold several)", "Gans 1967; Putnam 2000"),
        ("RL.informal", "list", None, "emergent roles from tokens + network position (clown, broker, gossip, confidant...)", "Johnson et al. 2003; Burt; Katz & Lazarsfeld; Jacobs"),
        ("RL.status", "enum", ["founder", "born_here", "recent_arrival", "contract_worker", "long_timer"], "arrival status", "SP-413; McMurdo; psychology 03"),
        ("RL.master", "text", None, "the role others lead with", "Hughes 1945"),
        ("RL.prestige", "int", [1, 5], "catalogue (NORC/GSS anchors)", "NORC 1989; Hout, Smith & Marsden 2015"),
        ("RL.prominence", "float", U, "salience multiplier for this person's acts; story-hub pull", "Spoon River analysis (role-holders are hubs)"),
        ("RL.class", "enum", ["business", "working", "none"], "catalogue", "Lynd & Lynd 1929; McMurdo science/support"),
        ("RL.knows", "list", None, "privileged knowledge channels (extra witnesses)", "role sets (Merton)"),
        ("RL.set", "list", None, "the role set: whom the role deals with (adds ties)", "Merton 1957"),
        ("RL.strain", "float", U, "role overload / conflict, adds to S.stress", "Goode 1960"),
        ("W.roles", "map", None, "roles the settlement needs and how many", "research/roles/04 x settlement record"),
        ("W.vacant", "list", None, "critical formal/informal roles vacant or contested", "research/roles/05 section 2-3"),
        ("W.cohesion", "float", U, "share of critical informal roles filled by consensus", "Johnson, Boster & Palinkas 2003; Palinkas 2000")]:
    t(k, kind, r, d, s_, prompt="words")

# daily life: places, money, addiction, travel (research/lives/)
for k, kind, r, d, s_, stored in [
        ("LIFE.home", "text", None, "home building or flat over a shop (NpcHouseholds, NpcPlaces.flats)", "households; research/lives/05", False),
        ("LIFE.work", "text", None, "workplace unit (bake_lives: occupation x distance x posts left)", "research/lives/01, 05", True),
        ("LIFE.school", "text", None, "school, college or childcare unit", "research/lives/05", True),
        ("LIFE.regulars", "map", None, "purpose -> the regular place (Huff gravity; same-town bonus)", "Huff 1963; research/lives/05", True),
        ("LIFE.today", "list", None, "the day's stays: work, school, worship, errands, leisure, strolls (pure of pid, day)", "research/lives/05", False),
        ("LIFE.now", "text", None, "where they are and what they're doing this hour; on the way where, and how", "NpcLife.state", False),
        ("LIFE.commute", "enum", ["drive", "carpool", "transit", "walk", "bike", "remote", "school_bus", "none", "driven"], "trait commute_mode", "ACS 2023", True),
        ("LIFE.car", "enum", ["own_car", "shared_car", "none"], "trait car_access", "ACS 2023 (~8% of households have no vehicle)", True),
        ("MONEY.wage", "float", None, "trait wage (occupation median x age x lognormal)", "BLS OEWS 2024", True),
        ("MONEY.savings", "float", None, "trait savings", "Fed SHED 2023; SCF", True),
        ("MONEY.debt", "float", None, "trait debt, with debts tags", "Fed SHED 2023; NY Fed HHDC", True),
        ("MONEY.finances", "enum", ["dependent", "wealthy", "comfortable", "getting_by", "struggling", "in_debt"], "trait finances", "Fed SHED 2023 (72% at least okay)", True),
        ("MONEY.style", "enum", ["saver", "careful", "spender", "generous", "tight", "anxious"], "trait money_style", "research/lives/02", True),
        ("MONEY.reasons", "list", None, "why they have what they have (inherited, laid_off, two_jobs...)", "research/lives/02", True),
        ("ADDICT.list", "list", None, "trait addictions (13 kinds)", "NSDUH 2023; research/lives/03", True),
        ("ADDICT.stage", "enum", ["none", "at_risk", "active", "recovering", "relapsed"], "trait addiction_stage", "transtheoretical / recovery literature", True),
        ("ADDICT.severity", "float", U, "trait addiction_severity", "DSM-5 severity (mild/moderate/severe)", True),
        ("FAITH.worship", "enum", ["weekly", "monthly", "seldom", "never"], "trait worship", "Gallup 2021-23", True)]:
    t(k, kind, r, d, s_, stored=stored, prompt="life card")

out = {"_about": "Story-engine token catalogue (research/psychology/06_story_engine_framework.md). "
                  "'stored': whether the value is saved (only the stored L0-L2 traits, the event log, and deltas "
                  "for people the player met); everything else is a pure function. 'prompt': how the token renders "
                  "into the Groq card -- 'band' = very low / low / (omitted 0.4-0.6) / high / very high words. "
                  "Generated by tools/story/make_tokens.py.",
       "version": 1, "tokens": T}
root = os.path.join(os.path.dirname(__file__), "..", "..")
path = os.path.join(root, "research", "psychology", "tokens.json")
with open(path, "w") as f:
    json.dump(out, f, indent=1)
kinds = {}
for x in T:
    kinds[x["id"].split(".")[0]] = kinds.get(x["id"].split(".")[0], 0) + 1
print("%d tokens -> %s  %s" % (len(T), os.path.relpath(path, root), kinds))
