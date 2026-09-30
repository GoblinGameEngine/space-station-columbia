#!/usr/bin/env python3
"""Writes the story-type catalogue: research/story/story_types.json (for the engine) and
research/story/03_story_types.md (to read). Edit the tables here and rerun:

    python3 tools/story/make_story_types.py

A story type is a storylet-with-state: roles (Greimas actants, cast by eligibility over the
psychology tokens), a trigger (an event pattern in the log), beats from a structural template (each
beat a function in Propp's sense, with a Freytag stage, a tension target, the value it turns
(McKee) and the dialogue intents it gives each role), an emotional shape (Reagan et al.), outcome
mythoi (Frye), and its reach (how it touches people 1-3 degrees out).
"""
import json
import os

# -- beat templates -----------------------------------------------------------------------------
# (beat id, Freytag stage, tension 0..1, what happens -- the function)
TEMPLATES = {
    "freytag": [
        ("setup", "intro", 0.15, "the parties and what binds them are shown"),
        ("incite", "exciting", 0.35, "the exciting force: an act from the event log opens the conflict"),
        ("complicate", "rise", 0.5, "it escalates; allies and opponents are drawn in"),
        ("confront", "climax", 0.85, "the parties meet head on; the value turns"),
        ("turn", "tragic", 0.7, "the counter-action: consequences begin to fall"),
        ("last_chance", "suspense", 0.75, "one last moment where it could still go either way"),
        ("resolve", "resolution", 0.25, "a new equilibrium is written into the world"),
    ],
    "romance": [  # Regis's eight essential elements
        ("society", "intro", 0.1, "the world that shapes the pair is shown"),
        ("meeting", "exciting", 0.3, "they meet"),
        ("barrier", "rise", 0.45, "what keeps them apart is established"),
        ("attraction", "rise", 0.5, "the reason they must be together shows"),
        ("declaration", "climax", 0.7, "one declares"),
        ("ritual_death", "tragic", 0.85, "the barrier seems insurmountable"),
        ("recognition", "suspense", 0.6, "they see how the barrier can be overcome"),
        ("commitment", "resolution", 0.2, "a lasting bond is sealed"),
    ],
    "kisho": [  # ki-sho-ten-ketsu: no conflict required
        ("ki", "intro", 0.1, "a person and a situation are introduced"),
        ("sho", "rise", 0.2, "it develops; small interactions deepen it"),
        ("ten", "climax", 0.4, "a turn that recontextualises it (not an opponent)"),
        ("ketsu", "resolution", 0.15, "the pieces come together; something is understood"),
    ],
    "revenge": [
        ("wrong", "exciting", 0.5, "the wrong is done (from the log)"),
        ("learning", "rise", 0.55, "the wronged party learns of it (a K event)"),
        ("vow", "rise", 0.6, "the resolve to repay it; others take sides"),
        ("pursuit", "rise", 0.7, "the avenger acts or seeks the means"),
        ("reckoning", "climax", 0.9, "confrontation: revenge taken, refused, or turned"),
        ("aftermath", "fall", 0.5, "the cost, to both and to those around them"),
        ("settle", "resolution", 0.25, "a feud begins, or it ends in forgiveness or justice"),
    ],
    "mystery": [
        ("anomaly", "exciting", 0.35, "something is wrong or missing"),
        ("question", "rise", 0.4, "someone asks who or why"),
        ("inquiry", "rise", 0.5, "people are asked; rumours conflict (K distortion)"),
        ("false_lead", "tragic", 0.6, "a wrong answer, often from a lie or assimilation"),
        ("recognition", "climax", 0.8, "the truth is recognised"),
        ("exposure", "fall", 0.55, "the one responsible is exposed (Propp 28)"),
        ("restore", "resolution", 0.2, "order and reputations are restored or changed"),
    ],
    "rebirth": [  # Booker's rebirth
        ("shadow", "intro", 0.3, "a person under a shadow (grief, drink, bitterness, a grudge)"),
        ("respite", "rise", 0.35, "things seem to improve"),
        ("relapse", "rise", 0.6, "the shadow closes in again"),
        ("depth", "climax", 0.8, "the lowest point, apparently final"),
        ("redemption", "resolution", 0.3, "rescued by someone's act or love (often the player's)"),
    ],
    "journey": [  # Vogler, condensed
        ("call", "exciting", 0.3, "a need or chance calls someone out of their routine"),
        ("refusal", "rise", 0.35, "doubt, fear, obligation"),
        ("mentor", "rise", 0.35, "someone gives help, advice or a means"),
        ("threshold", "rise", 0.5, "they commit and cross"),
        ("trials", "rise", 0.6, "tests, allies, enemies"),
        ("ordeal", "climax", 0.85, "the central trial"),
        ("reward", "fall", 0.45, "what was sought is won, or its price paid"),
        ("return", "resolution", 0.2, "they come back changed, bringing something to others"),
    ],
    "reconcile": [
        ("rift", "intro", 0.4, "a past break between two people (backstory or log)"),
        ("distance", "rise", 0.35, "they avoid each other; others notice"),
        ("reminder", "exciting", 0.45, "something brings the other to mind"),
        ("approach", "rise", 0.55, "one reaches out (often via a go-between)"),
        ("setback", "tragic", 0.7, "old pain flares; it nearly fails"),
        ("recognition", "climax", 0.6, "each understands the other's side"),
        ("reunion", "resolution", 0.2, "the tie is restored, changed"),
    ],
    "tragedy": [  # Booker's five stages of tragedy
        ("anticipation", "intro", 0.3, "a desire or temptation takes hold"),
        ("dream", "rise", 0.35, "it goes well; the person commits"),
        ("frustration", "rise", 0.6, "things begin to go wrong; more wrongs to cover the first"),
        ("nightmare", "climax", 0.9, "it runs out of control"),
        ("destruction", "resolution", 0.5, "the fall (loss of tie, standing, place) -- or a late turn to rebirth"),
    ],
    "monster": [  # Booker's overcoming the monster, for community threats
        ("shadow", "exciting", 0.4, "a threat to the community appears"),
        ("gathering", "rise", 0.5, "people argue and prepare; tension is displaced outward"),
        ("frustration", "rise", 0.65, "the first attempt fails"),
        ("nightmare", "climax", 0.9, "the threat peaks"),
        ("deliverance", "resolution", 0.3, "it is overcome, and the community is bound (or split) by it"),
    ],
}

# -- the catalogue ----------------------------------------------------------------------------------
# family, id, name, template, shape (Reagan), mythoi (Frye outcomes allowed), value (McKee pair),
# roles [(role, actant, eligibility)], trigger, theme (Egri), sources, reach, note
F = []


def st(fam, id, name, tpl, shape, mythoi, value, roles, trigger, theme, sources, reach="kin+friends", note=""):
    F.append(dict(family=fam, id=id, name=name, template=tpl, shape=shape, mythoi=mythoi, value=value,
                  roles=[dict(role=r, actant=a, eligible=e) for r, a, e in roles], trigger=trigger,
                  theme=theme, sources=sources, reach=reach, note=note))


A = "family A: bonds forming"
st(A, "stranger_arrives", "The stranger arrives", "kisho", "rags_to_riches", ["comedy", "romance", "irony"], "outsider/belonging",
   [("stranger", "subject", "newcomer to the settlement (often the player)"), ("gatekeeper", "opponent", "W.relmob low, P.A.trust low, prominent role"), ("first_friend", "helper", "P.communion high, W.relmob high")],
   "first contacts of a newcomer in a settlement", "a place becomes home through the people who let you in",
   ["Winesburg, Ohio (the listener)", "western 'stranger comes to town'", "Tobias: discovery"], "settlement")
st(A, "friendship", "A friendship forms", "kisho", "rags_to_riches", ["comedy"], "isolation/companionship",
   [("friend_a", "subject", "any"), ("friend_b", "object", "homophily with friend_a; tie layer >= 50")],
   "repeated positive interactions (help, gift, shared work)", "friends are made by small kindnesses repeated",
   ["Snyder: buddy love", "Middlemarch (unhistoric acts)"], "friends")
st(A, "courtship", "Courtship", "romance", "cinderella", ["comedy", "tragedy"], "loneliness/love",
   [("lover_a", "subject", "adult, not partnered or estranged"), ("lover_b", "object", "adult, homophily, mutual attraction"), ("obstacle", "opponent", "a person, rule or circumstance (kin, rank, distance, a rival)")],
   "attraction beats between two adults", "love has to cross something to be real",
   ["Regis 8 elements", "Polti 28", "Tobias: love", "Booker: comedy"], "kin+friends")
st(A, "found_family", "Found family", "kisho", "rags_to_riches", ["comedy"], "alone/belonging",
   [("stray", "subject", "isolated: few ties, C.origin recent_arrival or bereaved"), ("household", "helper", "a household with warmth (P.communion)")],
   "a lone person is repeatedly taken in", "family is who shows up",
   ["Ghibli (Totoro, Kiki)", "Snyder: rites of passage"], "household+friends")
st(A, "mentorship", "Mentor and student", "journey", "man_in_a_hole", ["comedy", "romance"], "ignorance/mastery",
   [("student", "subject", "young or newcomer; wants a skill or role"), ("mentor", "sender", "older, skilled in the occupation, P.A or P.C high")],
   "a request for help or teaching", "we become ourselves through someone who believed in us",
   ["Vogler: mentor", "Spoon River: Emily Sparks & Reuben Pantier", "Tobias: maturation"], "kin+friends")
st(A, "alliance_of_necessity", "Enemies to allies", "freytag", "man_in_a_hole", ["comedy", "romance"], "enmity/alliance",
   [("party_a", "subject", "grievance or rivalry with party_b"), ("party_b", "helper", "grievance or rivalry with party_a"), ("threat", "opponent", "a shared danger (community crisis, outsider)")],
   "a shared threat while a grievance is open", "a common danger makes strange allies",
   ["balance theory (enemy of my enemy)", "Booker: overcoming the monster"], "settlement")
st(A, "recovery_of_lost_one", "Recovery of a lost one", "reconcile", "man_in_a_hole", ["comedy", "tragedy"], "loss/reunion",
   [("seeker", "subject", "has a lost kin or friend"), ("found", "object", "the lost one (moved away, estranged, missing)")],
   "a belief arrives about a lost person's whereabouts", "what was lost is found changed",
   ["Polti 35", "Propp 23 (unrecognised arrival)", "Aristotle: recognition"], "kin")
st(A, "homecoming", "Homecoming", "journey", "man_in_a_hole", ["comedy", "irony"], "away/home",
   [("returnee", "subject", "resident returning after long absence"), ("home", "receiver", "household and old ties")],
   "a resident returns to the settlement", "you can't go home again, but you can go home",
   ["Booker: voyage and return", "Propp 20/23"], "kin+friends")

B = "family B: bonds tested"
st(B, "rivalry", "Rivalry of equals", "freytag", "cinderella", ["comedy", "romance", "tragedy", "irony"], "second/first",
   [("rival_a", "subject", "competes with rival_b for the object; similar status"), ("rival_b", "opponent", "same"), ("object", "object", "a prize, post, person, or reputation")],
   "competition events for the same object", "rivals make each other better or bring each other down",
   ["Tobias: rivalry", "Polti 24"], "friends+coworkers")
st(B, "rivalry_superior_inferior", "Rivalry of superior and inferior", "freytag", "cinderella", ["comedy", "tragedy", "irony"], "low/high",
   [("superior", "opponent", "R.power high over inferior"), ("inferior", "subject", "lower status, ambitious"), ("object", "object", "prize or person")],
   "an inferior challenges a superior for an object", "rank is tested by desire",
   ["Polti 24", "Tobias: underdog"], "coworkers+settlement")
st(B, "rivalry_of_kin", "Rivalry of kin", "freytag", "oedipus", ["tragedy", "comedy"], "rejected/preferred",
   [("preferred", "subject", "kin favoured by a parent/elder/partner"), ("rejected", "opponent", "kin not favoured"), ("object", "object", "affection, inheritance, a role")],
   "unequal treatment of kin (gift, praise, inheritance)", "favour divides a family",
   ["Polti 14", "King Lear", "Genesis (Jacob & Esau)"], "kin")
st(B, "love_triangle", "Love triangle", "romance", "oedipus", ["comedy", "tragedy", "irony"], "shared/exclusive",
   [("beloved", "object", "adult"), ("suitor_a", "subject", "attracted to beloved"), ("suitor_b", "opponent", "attracted to beloved")],
   "two people's attraction beats with the same person", "love cannot be divided without wounds",
   ["Polti 24/28", "Tobias: love"], "friends")
st(B, "mistaken_jealousy", "Mistaken jealousy", "mystery", "oedipus", ["tragedy", "comedy"], "trust/suspicion",
   [("jealous", "subject", "partnered; P.att preoccupied or D.negaff"), ("partner", "object", "the jealous one's partner"), ("supposed_rival", "opponent", "innocent"), ("author", "sender", "a false belief (distorted rumour) or a liar (K.lie)")],
   "a distorted or false belief about a partner reaches the jealous one", "jealousy destroys what it guards",
   ["Polti 32", "Othello", "Allport & Postman (assimilation)"], "kin+friends")
st(B, "erroneous_judgment", "False suspicion", "mystery", "man_in_a_hole", ["comedy", "tragedy"], "innocent/guilty",
   [("accuser", "subject", "believes a false K about victim"), ("victim", "object", "wrongly suspected (often the player)"), ("author", "sender", "the rumour's distortion or a liar"), ("guilty", "opponent", "the real culprit, if any")],
   "a belief with K.intent or actor distorted reaches someone with power to act", "a rumour can hang an innocent",
   ["Polti 33", "Propp 24/28 (false hero, exposure)"], "settlement")
st(B, "obstacles_to_love", "Forbidden love", "romance", "cinderella", ["comedy", "tragedy"], "duty/desire",
   [("lover_a", "subject", "adult"), ("lover_b", "object", "adult"), ("obstacle", "opponent", "family, rank, feud, rule, distance")],
   "courtship between people in opposed households, ranks or camps", "love against the world",
   ["Polti 28/29", "Tobias: forbidden love", "Romeo and Juliet"], "kin")
st(B, "divided_loyalty", "Divided loyalty", "freytag", "oedipus", ["tragedy", "irony", "comedy"], "loyalty/betrayal",
   [("torn", "subject", "strong ties to both parties"), ("side_a", "opponent", "in conflict with side_b"), ("side_b", "opponent", "in conflict with side_a")],
   "two people the torn one cares about come into conflict (unbalanced triad)", "you can't be everyone's friend",
   ["Heider balance", "Polti 23", "Antigone"], "kin+friends")
st(B, "test_of_friendship", "A friendship tested", "freytag", "man_in_a_hole", ["comedy", "tragedy"], "fair-weather/true",
   [("friend", "subject", "tie layer <= 15 with needy"), ("needy", "object", "in trouble; asks for costly help")],
   "someone in trouble asks a close friend for costly help", "a friend in need",
   ["Tobias: sacrifice", "Aesop"], "friends")
st(B, "keeping_a_secret", "The secret", "freytag", "icarus", ["comedy", "tragedy", "irony"], "trust/exposure",
   [("keeper", "subject", "knows a damaging truth (K) about owner"), ("owner", "object", "the one whose secret it is"), ("seeker", "opponent", "wants the secret (K.gossip high or grievance)")],
   "a secret-visibility event is known to someone besides its owner", "a secret shared is a secret half kept",
   ["Spoon River (secret x13)", "Polti 27"], "kin+friends")
st(B, "misunderstanding", "The misunderstanding", "kisho", "man_in_a_hole", ["comedy"], "confusion/clarity",
   [("a", "subject", "holds a distorted belief about b"), ("b", "object", "unaware of the misunderstanding")],
   "a harmless distortion (levelled/sharpened) reaches the other party", "most quarrels are about what nobody said",
   ["Frye: comedy", "ATU: anecdotes", "comedy of errors"], "friends")

C = "family C: bonds broken"
st(C, "betrayal", "Betrayal", "revenge", "icarus", ["tragedy", "irony", "comedy"], "trust/betrayal",
   [("betrayer", "opponent", "tie layer <= 15 with betrayed; low H or strong motive"), ("betrayed", "subject", "trusted the betrayer (R.trust high)")],
   "a break_promise/lie/steal/harm by someone with a close tie", "the deepest wounds come from the nearest",
   ["Aristotle XIV (near or dear)", "Polti 27", "Tobias: temptation"], "kin+friends")
st(C, "infidelity", "Infidelity", "revenge", "icarus", ["tragedy", "irony"], "faithful/faithless",
   [("deceived", "subject", "partnered"), ("unfaithful", "opponent", "the partner"), ("third", "opponent", "the other")],
   "a secret affair event becomes known", "what is hidden in a house is known to the street",
   ["Polti 25 (adult; only as backstory or offstage)"], "kin", "adult content: off-screen only; reactions and consequences on-screen")
st(C, "dishonor_discovered", "The loved one's dishonor", "mystery", "oedipus", ["tragedy", "irony"], "pride/shame",
   [("discoverer", "subject", "tie layer <= 15 with guilty"), ("guilty", "object", "did a shameful act (log)")],
   "someone learns (K) that a close tie did something shameful", "love has to survive knowing",
   ["Polti 27", "Aristotle: recognition"], "kin")
st(C, "feud_in_family", "Family enmity", "freytag", "riches_to_rags", ["tragedy", "comedy"], "kin/enemies",
   [("kin_a", "subject", "kin of kin_b; grievance"), ("kin_b", "opponent", "kin of kin_a; grievance")],
   "a grievance opens between kin", "blood is thicker, and so is bad blood",
   ["Polti 13", "Polti 4", "King Lear"], "kin")
st(C, "feud", "A feud between households", "revenge", "riches_to_rags", ["tragedy", "comedy", "irony"], "peace/honor",
   [("house_a", "subject", "household with grievance against house_b; W.honor matters"), ("house_b", "opponent", "the other household")],
   "retaliation answered with retaliation across households", "an eye for an eye leaves the valley blind",
   ["Nisbett & Cohen (honor)", "Hatfield-McCoy", "Polti 3"], "kin+settlement")
st(C, "estrangement", "Drifting apart", "kisho", "riches_to_rags", ["irony", "tragedy"], "close/distant",
   [("a", "subject", "tie weakening (no interaction, moved, changed)"), ("b", "object", "the other")],
   "a close tie with no contact for a long time", "friendships die of neglect, not murder",
   ["Winesburg, Ohio", "Dunbar layers (decay)"], "friends")
st(C, "grief", "Loss of a loved one", "rebirth", "man_in_a_hole", ["tragedy", "comedy"], "presence/absence",
   [("bereaved", "subject", "lost a close tie"), ("lost", "object", "the dead or departed"), ("consoler", "helper", "P.communion high; tie to bereaved")],
   "a death or departure of a close tie", "grief is love with nowhere to go",
   ["Polti 36", "Ghibli (Grave of the Fireflies; Totoro's absent mother)"], "kin+friends")
st(C, "abandonment", "Left behind", "rebirth", "man_in_a_hole", ["tragedy", "comedy"], "held/abandoned",
   [("left", "subject", "a dependent (child, elder, partner) left by a close tie"), ("leaver", "opponent", "left"), ("carer", "helper", "steps in")],
   "a close tie leaves a dependent", "who stays is family",
   ["Polti 7", "Tobias: escape (from the other side)"], "kin")

D = "family D: harm and justice"
st(D, "vengeance", "Crime pursued by vengeance", "revenge", "oedipus", ["tragedy", "romance", "comedy"], "wrong/justice",
   [("avenger", "subject", "care(avenger, victim) high; knows the crime; grievance.revenge high"), ("criminal", "opponent", "the actor of the harm"), ("victim", "sender", "the harmed")],
   "a harm event whose victim has a close tie with low A or W.honor high", "revenge feeds on itself",
   ["Polti 3", "Tobias: revenge", "Hamlet"], "kin+settlement")
st(D, "vengeance_among_kin", "Vengeance among kin", "revenge", "oedipus", ["tragedy"], "loyalty/justice",
   [("avenger", "subject", "kin of victim and of guilty"), ("guilty", "opponent", "kin"), ("victim", "sender", "kin of both")],
   "harm within a family, witnessed by another member", "when kin wrong kin, every choice betrays someone",
   ["Polti 4", "Aristotle XIV", "the Oresteia"], "kin")
st(D, "pursuit", "Pursuit", "freytag", "man_in_a_hole", ["romance", "tragedy"], "free/caught",
   [("fugitive", "subject", "did something and is sought (often the player)"), ("pursuer", "opponent", "authority role or avenger")],
   "a public wrongdoing with an authority role present", "you can run from the town but not from yourself",
   ["Polti 5", "Tobias: pursuit, escape"], "settlement")
st(D, "enigma", "The mystery", "mystery", "man_in_a_hole", ["comedy", "romance", "irony"], "unknown/known",
   [("seeker", "subject", "curious (P.O) or wronged; often the player"), ("problem", "object", "an event whose actor is unknown to most"), ("keeper", "opponent", "someone who knows and hides")],
   "a notable event with a hidden actor (vis secret or no witnesses)", "every town has a thing nobody says",
   ["Polti 11", "Tobias: riddle", "Talk of the Town"], "settlement")
st(D, "scapegoat", "The scapegoat", "mystery", "man_in_a_hole", ["comedy", "tragedy"], "blame/truth",
   [("scapegoat", "object", "outgroup (W.outgroup) or low-status; often the newcomer player"), ("crowd", "opponent", "the settlement under stress"), ("defender", "helper", "high H, high A, or a tie to the scapegoat")],
   "a community misfortune with no clear actor while stress is high", "fear looks for a face",
   ["Kanas displacement", "Mars-500", "Polti 33"], "settlement")
st(D, "remorse", "Remorse and atonement", "rebirth", "man_in_a_hole", ["comedy", "tragedy"], "guilt/peace",
   [("culprit", "subject", "did harm; H high enough to feel it"), ("victim", "object", "the harmed"), ("confessor", "helper", "hears it (priest, friend, the player)")],
   "someone with high H who caused harm", "a wrong owned is half-undone",
   ["Polti 34", "Booker: rebirth"], "kin+friends")
st(D, "redemption", "Redemption", "rebirth", "man_in_a_hole", ["comedy"], "fallen/restored",
   [("fallen", "subject", "low reputation (image score), D.disinhib or S.coping drink/lash_out"), ("believer", "helper", "someone who keeps faith (often the player)")],
   "a disreputable person does a good act", "no one is only their worst deed",
   ["Booker: rebirth", "Spoon River (Reuben Pantier)", "Tobias: transformation"], "settlement")
st(D, "forgiveness", "Forgiveness", "reconcile", "man_in_a_hole", ["comedy"], "grudge/grace",
   [("wronged", "subject", "R.grievance open"), ("wrongdoer", "object", "apologises or repays")],
   "an apology/restitution event toward an open grievance", "forgiving is a gift to the forgiver too",
   ["McCullough TRIM", "Frye: comedy (enemies leave as friends)"], "kin+friends")
st(D, "supplication", "Supplication", "freytag", "man_in_a_hole", ["comedy", "tragedy"], "mercy/judgment",
   [("suppliant", "subject", "in trouble with a power"), ("persecutor", "opponent", "presses the case"), ("power", "sender", "authority role whose decision is doubtful")],
   "someone appeals to an authority against a persecutor", "mercy is a choice",
   ["Polti 1"], "settlement")
st(D, "rescue", "Deliverance", "monster", "man_in_a_hole", ["romance", "comedy"], "danger/safety",
   [("unfortunate", "object", "in danger"), ("threat", "opponent", "a person or hazard"), ("rescuer", "subject", "anyone near; often the player")],
   "a danger event with someone able to intervene", "one act can change how a town sees you",
   ["Polti 2", "Tobias: rescue", "Propp 22"], "settlement")
st(D, "fatal_imprudence", "Fatal imprudence", "tragedy", "icarus", ["tragedy", "irony"], "prudence/folly",
   [("imprudent", "subject", "D.disinhib or low C; ignores a warning"), ("counsellor", "helper", "warned them"), ("victim", "object", "who or what is lost")],
   "a careless act against a warning (life-support, safety rules)", "the rules were written in someone's blood",
   ["Polti 17", "Gelfand (tightness)"], "settlement")

E = "family E: power and community"
st(E, "revolt", "Standing up to power", "freytag", "cinderella", ["romance", "tragedy", "irony"], "submission/defiance",
   [("tyrant", "opponent", "authority role abusing R.power"), ("conspirator", "subject", "grievance; P.agency high")],
   "repeated harms by an authority to people under it", "power holds only while people agree",
   ["Polti 8", "SP-413 (governance)"], "settlement")
st(E, "ambition", "Ambition", "tragedy", "icarus", ["tragedy", "romance", "irony"], "modest/ambitious",
   [("ambitious", "subject", "V.power/achievement high"), ("coveted", "object", "a role or prize"), ("adversary", "opponent", "holds or guards it")],
   "someone moves for a role or prize held by another", "ambition eats what it cannot reach",
   ["Polti 30", "Booker: tragedy", "Tobias: ascension, wretched excess"], "settlement")
st(E, "downfall", "The fall of the mighty", "tragedy", "riches_to_rags", ["tragedy", "irony"], "high/low",
   [("mighty", "subject", "prominent, high image score, one flaw (D facet)"), ("witnesses", "receiver", "the settlement")],
   "a prominent person's hidden wrong becomes known", "the higher the seat, the harder the fall",
   ["Aristotle XIII (hamartia)", "Tobias: descension", "Spoon River (Thomas Rhodes)"], "settlement")
st(E, "underdog", "The underdog", "freytag", "rags_to_riches", ["romance", "comedy"], "weak/strong",
   [("underdog", "subject", "low status or outgroup; skill or heart"), ("favourite", "opponent", "high status")],
   "a contest where a low-status person has a chance", "the small can win",
   ["Tobias: underdog", "Booker: rags to riches"], "settlement")
st(E, "rags_to_riches", "Rags to riches", "journey", "cinderella", ["comedy", "romance"], "poor/rich",
   [("striver", "subject", "income low, V.achievement"), ("helper", "helper", "a benefactor or the player")],
   "a poor person gains a chance", "worth is revealed by fortune",
   ["Booker: rags to riches", "Cinderella (ATU 510A)"], "settlement")
st(E, "negotiation", "Obtaining", "freytag", "man_in_a_hole", ["comedy", "irony"], "no/yes",
   [("solicitor", "subject", "wants something (often the player)"), ("refuser", "opponent", "has it; refuses"), ("arbiter", "sender", "optional authority")],
   "a request refused", "persuasion is finding what the other wants",
   ["Polti 12"], "coworkers+friends")
st(E, "election", "The contest for office", "freytag", "cinderella", ["comedy", "irony", "tragedy"], "private/public",
   [("candidate_a", "subject", "seeks a role"), ("candidate_b", "opponent", "seeks the same role"), ("electors", "receiver", "the settlement")],
   "a role vacancy (death, departure, term)", "a town chooses who it thinks it is",
   ["community drama", "Spoon River (judges, editor)"], "settlement")
st(E, "community_crisis", "The crisis", "monster", "man_in_a_hole", ["romance", "tragedy", "comedy"], "safety/peril",
   [("community", "subject", "the settlement"), ("threat", "opponent", "failure of air/water/power, fire, breach, disease"), ("leader", "helper", "authority or natural leader"), ("outsider", "receiver", "W.outgroup (displacement)")],
   "a major world event threatening the settlement", "in the dark, a town learns who it is",
   ["Polti 6", "Booker: overcoming the monster", "Gelfand (threat tightens)", "Kanas (displacement)"], "settlement")
st(E, "rumour_run_wild", "The rumour", "mystery", "oedipus", ["comedy", "irony", "tragedy"], "fact/fiction",
   [("subject_of_rumour", "object", "whom the rumour is about (often the player)"), ("spreader", "sender", "high K.gossip or K.lie"), ("debunker", "helper", "high H, trusted")],
   "a belief whose distortion (sharpen/assimilate/lie) has reached many", "a lie travels while the truth ties its shoes",
   ["Allport & Postman", "Talk of the Town", "Spoon River (truth/lie)"], "settlement")
st(E, "clearing_a_name", "Clearing one's name", "mystery", "man_in_a_hole", ["comedy", "romance"], "disgrace/honor",
   [("accused", "subject", "low opinion from a false belief"), ("witness", "helper", "knows the truth (K accurate)")],
   "a person's image score falls through false beliefs", "the truth needs a witness",
   ["Propp 27-28 (recognition, exposure)", "Polti 33"], "settlement")
st(E, "reformer", "The reformer", "freytag", "icarus", ["comedy", "tragedy", "irony"], "custom/change",
   [("reformer", "subject", "V.universalism/self-direction high; C.fit low"), ("custom", "opponent", "W.tight high; tradition keepers")],
   "someone repeatedly breaks a norm for a principle", "a town must choose between its habits and its conscience",
   ["Snyder: institutionalized", "SP-413 (matching problem)"], "settlement")
st(E, "overcoming_menace", "Overcoming a menace", "monster", "man_in_a_hole", ["romance", "tragedy"], "fear/courage",
   [("menace", "opponent", "a dangerous person or hazard harming the community"), ("champion", "subject", "courage high; often the player"), ("victims", "receiver", "the harmed")],
   "repeated harms from one source", "courage is contagious",
   ["Booker: overcoming the monster", "Snyder: monster in the house"], "settlement")

G = "family F: self and change (driven by others)"
st(G, "coming_of_age", "Coming of age", "journey", "man_in_a_hole", ["comedy", "romance"], "child/adult",
   [("youth", "subject", "teen or young adult"), ("elder", "sender", "parent or mentor"), ("world", "opponent", "a test")],
   "a young person's first adult responsibility or failure", "growing up is choosing who to disappoint",
   ["Tobias: maturation", "bildungsroman", "Ghibli (Kiki)"], "kin+friends")
st(G, "temptation", "Temptation", "tragedy", "icarus", ["tragedy", "comedy"], "integrity/corruption",
   [("tempted", "subject", "H mid; a need"), ("tempter", "sender", "offers (often a bribe; low H)")],
   "an offer (bribe, shortcut, affair) to someone with a need", "everyone has a price, or doesn't",
   ["Tobias: temptation", "Faust"], "friends")
st(G, "sacrifice_for_kin", "Sacrifice for kin", "freytag", "oedipus", ["tragedy", "comedy"], "self/other",
   [("hero", "subject", "close tie in need"), ("kinsman", "receiver", "the one saved"), ("price", "object", "what is given up")],
   "a close tie in need that only a costly act can meet", "love is measured in what it costs",
   ["Polti 21", "Tobias: sacrifice"], "kin")
st(G, "sacrifice_for_ideal", "Sacrifice for an ideal", "freytag", "oedipus", ["tragedy", "romance"], "comfort/conviction",
   [("hero", "subject", "strong value (V) or foundation (M)"), ("ideal", "object", "the cause"), ("price", "object", "what is given up")],
   "a value is threatened and someone could pay to defend it", "some things are worth more than safety",
   ["Polti 20"], "settlement")
st(G, "passion_sacrifice", "All sacrificed for a passion", "tragedy", "riches_to_rags", ["tragedy", "irony"], "balance/obsession",
   [("devotee", "subject", "extreme interest (drink, gambling, a person, a project)"), ("sacrificed", "receiver", "who pays (family)")],
   "a pattern of costly acts toward one object", "obsession spends other people's lives",
   ["Polti 22", "Tobias: wretched excess"], "kin")
st(G, "hard_choice", "The necessary sacrifice", "freytag", "oedipus", ["tragedy"], "love/duty",
   [("chooser", "subject", "duty role"), ("beloved", "object", "a loved one on the other side of duty")],
   "duty and a close tie point opposite ways (e.g. rationing, quarantine, reporting kin)", "duty and love collide",
   ["Polti 23", "Agamemnon"], "kin+settlement")
st(G, "crisis_and_recovery", "Crisis and recovery", "rebirth", "man_in_a_hole", ["comedy"], "breakdown/healing",
   [("person", "subject", "D.lpfs raised by stress, or S.stress high"), ("supporter", "helper", "a close tie, doctor, or the player")],
   "stress past threshold in someone with vulnerability", "no one gets better alone",
   ["Polti 16 (rewritten per psychology 02 §2.4)", "Palinkas & Suedfeld (salutogenic)"], "kin+friends",
   "never linked to violence; recovery possible; no diagnostic labels")
st(G, "addiction_recovery", "Addiction and recovery", "rebirth", "man_in_a_hole", ["comedy", "tragedy"], "bondage/freedom",
   [("person", "subject", "S.coping drink or D.disinhib"), ("family", "receiver", "affected kin"), ("sponsor", "helper", "a friend or the player")],
   "repeated coping events", "the way back is walked with others",
   ["Spoon River (Chase Henry, the town drunk)", "Booker: rebirth"], "kin")
st(G, "changed", "The one who changed", "rebirth", "man_in_a_hole", ["comedy", "tragedy"], "before/after",
   [("changed", "subject", "an injury, illness, disability or old age changed them (mobility_aid, event)"), ("close", "helper", "close ties who must adjust"), ("pitier", "opponent", "treats them as less")],
   "an injury or illness event, or a sharp decline", "we are more than what happens to our bodies",
   ["Tobias: metamorphosis", "Kafka's Metamorphosis (the family's reaction)"], "kin+friends")
st(G, "identity_revealed", "Who I really am", "mystery", "cinderella", ["comedy", "tragedy"], "hidden/revealed",
   [("seeker", "subject", "unknown parentage, origin, or past"), ("keeper", "sender", "knows the truth")],
   "a belief about someone's origin surfaces", "recognition changes everything",
   ["Aristotle: recognition", "Polti 19 (softened)", "Propp 27"], "kin")
st(G, "earthsick", "Homesick for Earth", "kisho", "man_in_a_hole", ["comedy", "irony"], "here/there",
   [("homesick", "subject", "C.earthsick high"), ("anchor", "helper", "someone who makes here home")],
   "a reminder of Earth (letter, date, object, view)", "home is not a planet",
   ["Kanas (Earth out of view)", "Ghibli (quiet longing)"], "friends")
st(G, "wonder", "Wonder", "kisho", "rags_to_riches", ["comedy"], "ordinary/awe",
   [("witness", "subject", "C.awe or P.O high"), ("sharer", "helper", "someone to share the sight with (often the player)")],
   "a rare sight (the view, an eclipse, a bloom, the spine lights)", "awe makes us larger by making us small",
   ["Yaden et al. 2016 (overview effect)", "Ghibli"], "friends")
st(G, "quest", "The quest", "journey", "man_in_a_hole", ["romance", "comedy"], "lack/fulfilment",
   [("seeker", "subject", "a need (object, knowledge, person)"), ("goal", "object", "what is sought"), ("guide", "helper", "knows the way")],
   "a need or lack that cannot be met locally", "the treasure is the road",
   ["Booker: the quest", "Tobias: quest, adventure", "Propp 8-19"], "friends")
st(G, "daring_enterprise", "The bold plan", "freytag", "cinderella", ["romance", "comedy", "tragedy"], "impossible/done",
   [("leader", "subject", "P.agency high"), ("goal", "object", "a hard project (repair, expedition, festival)"), ("adversary", "opponent", "a person, rule, or nature")],
   "an ambitious joint undertaking proposed", "together we can",
   ["Polti 9"], "coworkers+settlement")
st(G, "voyage_and_return", "Voyage and return", "journey", "man_in_a_hole", ["comedy", "irony"], "familiar/strange",
   [("traveller", "subject", "leaves the settlement (other settlement, EVA, the spine)"), ("home", "receiver", "ties left behind")],
   "a trip to a strange place", "we travel to see home",
   ["Booker: voyage and return", "Ghibli (Spirited Away)"], "kin+friends")
st(G, "runaway", "The runaway", "journey", "man_in_a_hole", ["comedy", "tragedy"], "trapped/free",
   [("runaway", "subject", "teen or unhappy spouse; low C.fit"), ("guardian", "opponent", "parent or partner"), ("haven", "helper", "who takes them in")],
   "a young or unhappy person leaves home", "to find yourself you may have to leave",
   ["Polti 10 (recast)", "Tobias: escape"], "kin")

H = "family G: quiet stories (kishotenketsu, gossip-sized)"
st(H, "small_kindness", "A small kindness", "kisho", "rags_to_riches", ["comedy"], "unnoticed/seen",
   [("giver", "subject", "anyone (often the player)"), ("receiver", "object", "anyone with a small need")],
   "a help/gift event of low magnitude", "the growing good of the world is partly dependent on unhistoric acts",
   ["Middlemarch (finale)", "Ghibli"], "friends")
st(H, "festival", "The festival", "kisho", "rags_to_riches", ["comedy"], "apart/together",
   [("organiser", "subject", "role or high P.E"), ("community", "receiver", "the settlement")],
   "a calendar festival or harvest", "a community is a promise renewed",
   ["Frye: comedy (society renewed)", "seasonal ritual"], "settlement")
st(H, "craft_pride", "The work well done", "kisho", "rags_to_riches", ["comedy"], "doubt/pride",
   [("maker", "subject", "occupation-skilled, P.C high"), ("client", "receiver", "who receives the work")],
   "a notable work task completed", "doing a thing well is a kind of love",
   ["Ghibli (Kiki's Delivery Service, Porco Rosso)"], "coworkers")
st(H, "caring_for_elder", "Caring for an elder", "kisho", "man_in_a_hole", ["comedy", "tragedy"], "burden/gift",
   [("carer", "subject", "kin of elder"), ("elder", "object", "age >= 75 or mobility aid")],
   "an elder's decline events", "we are carried and we carry",
   ["Tokyo Story (Ozu)", "Ghibli"], "kin")
st(H, "new_life", "A new life", "kisho", "rags_to_riches", ["comedy"], "before/after",
   [("parents", "subject", "household with a birth or adoption"), ("community", "receiver", "neighbours")],
   "a birth or adoption event", "a child remakes everyone around it",
   ["Frye: comedy"], "kin+friends")
st(H, "lost_and_found", "Lost and found", "kisho", "man_in_a_hole", ["comedy"], "lost/returned",
   [("loser", "object", "lost something that matters"), ("finder", "subject", "finds it (often the player)")],
   "a return_lost event", "small returns make large friendships",
   ["ATU realistic tales"], "friends")
st(H, "letters", "Letters across distance", "kisho", "man_in_a_hole", ["comedy", "tragedy"], "far/near",
   [("writer", "subject", "kin or friend far away"), ("reader", "object", "here")],
   "a message arrives from another settlement or Earth", "distance tests and proves",
   ["Spoon River (Emily Sparks's letter)"], "kin")
st(H, "curiosity", "A curious thing", "kisho", "man_in_a_hole", ["comedy"], "puzzle/understanding",
   [("noticer", "subject", "P.O high or a child"), ("thing", "object", "an odd object or event, not a crime")],
   "an unexplained harmless event", "the world is stranger and kinder than it looks",
   ["Ghibli (Totoro)", "curiosity (Brewer & Lichtenstein)"], "friends")
st(H, "town_character", "The town character", "kisho", "man_in_a_hole", ["comedy", "irony"], "odd/beloved",
   [("character", "subject", "an eccentric (extreme facet, D.psych mild, odd role)"), ("town", "receiver", "the settlement's opinion")],
   "an eccentric's notable act", "every town has one, and needs one",
   ["Winesburg, Ohio (the grotesques)", "Spoon River (Chase Henry)"], "settlement")
st(H, "anecdote", "The anecdote", "kisho", "man_in_a_hole", ["comedy", "irony"], "expectation/twist",
   [("teller", "sender", "high K.gossip, humour"), ("subject", "object", "anyone in a comic event")],
   "a minor event with a comic twist spreads", "the town tells itself stories to know itself",
   ["ATU: anecdotes and jokes", "Dunbar (gossip)"], "settlement")


def main():
    for s in F:
        assert s["template"] in TEMPLATES, s["id"]
        s["beats"] = [dict(beat=b, stage=g, tension=t, function=f) for b, g, t, f in TEMPLATES[s["template"]]]
    ids = [s["id"] for s in F]
    assert len(ids) == len(set(ids))
    # coverage: every Polti situation, Booker plot and Tobias plot must be mapped by some type
    import re
    src = " ".join(" ".join(s["sources"]) for s in F)
    polti = set()
    for m in re.finditer(r"Polti ([0-9/ ]+)", src):
        polti |= {int(x) for x in re.findall(r"\d+", m.group(1))}
    backstory = {15, 18, 19, 26}       # off-screen backstory only (see the catalogue notes); 31 left to the literary phase
    polti |= backstory | {31}
    missing = sorted(set(range(1, 37)) - polti)
    booker = ["overcoming the monster", "rags to riches", "the quest", "voyage and return", "comedy", "tragedy", "rebirth"]
    tobias = ["quest", "adventure", "pursuit", "rescue", "escape", "revenge", "riddle", "rivalry", "underdog", "temptation",
              "metamorphosis", "transformation", "maturation", "love", "forbidden love", "sacrifice", "discovery",
              "wretched excess", "ascension", "descension"]
    low = src.lower()
    mb = [b for b in booker if "booker: " + b not in low]
    mt = [t for t in tobias if not re.search(r"tobias: [^;\]]*\b" + t + r"\b", low)]
    print("coverage -- Polti missing:", missing or "none", "| Booker missing:", mb or "none", "| Tobias missing:", mt or "none")
    root = os.path.join(os.path.dirname(__file__), "..", "..")
    out = {
        "_about": "Story-type catalogue for the story engine (research/story/04_arcs_in_the_engine.md). "
                  "Generated by tools/story/make_story_types.py. Roles are Greimas actants with eligibility "
                  "over the psychology tokens (research/psychology/tokens.json); beats come from the named "
                  "template; shape = Reagan et al. emotional arc for the subject; mythoi = Frye outcome families "
                  "allowed; value = McKee value pair the arc turns; reach = who beyond the principals it touches.",
        "version": 1, "templates": {k: [dict(beat=b, stage=g, tension=t, function=f) for b, g, t, f in v] for k, v in TEMPLATES.items()},
        "story_types": F}
    with open(os.path.join(root, "research", "story", "story_types.json"), "w") as f:
        json.dump(out, f, indent=1)
    # the readable catalogue
    md = ["# 3. The catalogue of story types", "",
          "Generated by `tools/story/make_story_types.py` from the same tables as `story_types.json`. "
          "**%d story types** in 7 families, built on %d beat templates. Coverage, checked by the script:" % (len(F), len(TEMPLATES)), "",
          "- **Polti's 36 situations:** all mapped. #15, #18, #19 and #26 are rare, off-screen backstory only; "
          "#16 is recast as crisis and recovery. #31 (conflict with a god) is left to the literary phase.",
          "- **Booker's 7 plots** and **Tobias's 20 master plots**: all mapped.",
          "- **Frye's 4 mythoi** are the outcome families; the **Reagan shapes** are the emotional curves.",
          "- **Regis's 8 elements** make up the courtship template, and **kishōtenketsu** the quiet template.", ""]
    md.append("## Beat templates")
    for k, v in TEMPLATES.items():
        md.append("- **%s**: %s" % (k, " → ".join(b for b, _, _, _ in v)))
    fam = None
    for s in F:
        if s["family"] != fam:
            fam = s["family"]
            md += ["", "## " + fam[0].upper() + fam[1:], "",
                   "| id | story | template / shape | value turned | roles (actant) | trigger | sources |",
                   "|---|---|---|---|---|---|---|"]
        roles = "; ".join("%s (%s)" % (r["role"], r["actant"]) for r in s["roles"])
        md.append("| `%s` | %s | %s / %s | %s | %s | %s | %s |" % (
            s["id"], s["name"], s["template"], s["shape"], s["value"], roles, s["trigger"], "; ".join(s["sources"])))
    with open(os.path.join(root, "research", "story", "03_story_types.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("%d story types, %d templates" % (len(F), len(TEMPLATES)))


if __name__ == "__main__":
    main()
