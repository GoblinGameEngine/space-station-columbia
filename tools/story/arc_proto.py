#!/usr/bin/env python3
"""Prototype: player history as a series of story arcs (research/story/04_arcs_in_the_engine.md).

Runs 60 days in a generated settlement (tools/story/propagation_proto.py). The player acts; each act
is logged; word of it spreads through the deterministic cascade; story sifting patterns spot arcs
forming (story_types.json ids); a drama manager with a storyteller personality decides which live
arc's next beat to surface each day, steering tension toward its target curve; arcs resolve into a
mythos (Frye) and write deltas. Prints the player's arc history, tension vs target, and the [STORY]
card an NPC in a live arc would carry into its Groq prompt.

    python3 tools/story/arc_proto.py [seed] [storyteller: cassandra|phoebe]
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import propagation_proto as pp  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
TYPES = {t["id"]: t for t in json.load(open(os.path.join(ROOT, "research", "story", "story_types.json")))["story_types"]}

VERBS = {  # valence toward the patient, magnitude, weight for spread
    "help": (+1, 1, 0.35), "gift": (+1, 1, 0.35), "rescue": (+1, 3, 1.2), "return_lost": (+1, 1, 0.4),
    "insult": (-1, 1, 0.45), "steal": (-1, 2, 0.7), "break_promise": (-1, 1, 0.5), "apologize": (+1, 1, 0.35),
}
STORYTELLERS = {
    # target tension by day: cassandra rises and falls in waves; phoebe mostly calm with rare peaks
    "cassandra": lambda d: 0.3 + 0.35 * max(0.0, math.sin(d / 60.0 * 3 * math.pi)),
    "phoebe": lambda d: 0.2 + 0.25 * max(0.0, math.sin(d / 60.0 * 2 * math.pi)) ** 3,
}


class Arc:
    def __init__(self, tid, day, roles, why):
        self.t = TYPES[tid]
        self.id = tid
        self.day = day
        self.roles = roles
        self.why = why
        self.beat = 0
        self.log = [(day, self.t["beats"][0]["beat"])]
        self.outcome = None

    def tension(self):
        return self.t["beats"][min(self.beat, len(self.t["beats"]) - 1)]["tension"]

    def next_tension(self):
        return self.t["beats"][min(self.beat + 1, len(self.t["beats"]) - 1)]["tension"]

    def advance(self, day):
        if self.beat < len(self.t["beats"]) - 1:
            self.beat += 1
            self.log.append((day, self.t["beats"][self.beat]["beat"]))
        return self.beat == len(self.t["beats"]) - 1


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    teller = sys.argv[2] if len(sys.argv) > 2 else "cassandra"
    rng = random.Random(seed)
    people, adj = pp.build(seed, 400)
    n = len(people)
    ties = {i: {v: l for v, l in adj[i]} for i in range(n)}

    def care(x, q):
        if x == q:
            return 1.0
        return pp.LAYER_STRENGTH.get(ties[x].get(q), 0.0)

    log = []          # events
    known = {}        # event id -> {person: (day, hops)}
    arcs, done = [], []
    opinion_hist = []
    tension_hist = []
    counts = {}

    def know(x, e, day):
        k = known[e["id"]].get(x)
        return k is not None and e["day"] + k[0] <= day

    def opinion(x, day):
        o = 0.0
        for e in log:
            if e["actor"] != "PLAYER" or not know(x, e, day):
                continue
            val, mag, _ = VERBS[e["verb"]]
            c = care(x, e["patient"])
            hops = known[e["id"]][x][1]
            w = val * mag * max(c, 0.15) * (0.7 ** hops)
            o += w * (2.5 if w < 0 else 1.0)      # negativity bias
        return o

    def resolve(a, day):
        """The arc's ending (Frye mythos), from the world state when it resolves."""
        if a.id == "vengeance":
            return "tragedy" if opinion(a.roles["avenger"], day) < -1.0 else "irony"
        if a.id == "scapegoat":
            town = sum(opinion(x, day) for x in range(0, n, 5)) / len(range(0, n, 5))
            return "comedy" if town > 0 else "tragedy"
        if a.id == "rumour_run_wild":
            return "irony"
        return a.t["mythoi"][0]

    crisis_day = 32
    circle = rng.sample(range(n), 20)
    MAX_FEATURED = {"cassandra": 4, "phoebe": 3}[teller]
    QUIET_SLOTS = 1                               # always room for a quiet (kishotenketsu) arc

    def quiet(a):
        return a.t["template"] == "kisho"
    background = []
    merged = [0]

    def closeness_to_player(x):
        return max((care(x, e["patient"]) for e in log if e["actor"] == "PLAYER"), default=0.0)

    def open_arc(tid, day, roles, why, key=None):
        """Sifted candidate -> merged into a live arc of the same key, featured, or background."""
        for a in arcs + background:
            if key is not None and getattr(a, "key", None) == key and a.outcome is None:
                merged[0] += 1
                a.why += "; " + why
                return a
        a = Arc(tid, day, roles, why)
        a.key = key
        # ST.quality, reduced: stakes x closeness x novelty (psychology/story 02 section 2.3)
        stakes = max(b["tension"] for b in a.t["beats"])
        people_in = [v for v in roles.values() if isinstance(v, int)]
        close = max([closeness_to_player(v) for v in people_in] + [0.3])
        recent = [x.id for x in sorted(arcs, key=lambda x: -x.day)[:3]]
        mean_t = sum(b["tension"] for b in a.t["beats"]) / len(a.t["beats"])
        fit = 1.0 - abs(mean_t - STORYTELLERS[teller](day))      # the storyteller's pacing, at admission
        a.quality = stakes * (0.5 + close) * (0.6 if tid in recent else 1.0) * (0.4 + fit)
        featured = [x for x in arcs if x.outcome is None]
        loud = [x for x in featured if not quiet(x)]
        room = MAX_FEATURED - QUIET_SLOTS if not quiet(a) else MAX_FEATURED
        if (quiet(a) and len(featured) < MAX_FEATURED) or (not quiet(a) and len(loud) < room and len(featured) < MAX_FEATURED):
            arcs.append(a)
        else:
            same = [x for x in featured if quiet(x) == quiet(a)] or featured
            worst = min(same, key=lambda x: x.quality)
            if a.quality > worst.quality * 1.2 and worst.beat == 0:
                arcs.remove(worst)
                background.append(worst)
                arcs.append(a)
            else:
                background.append(a)
        return a
    for day in range(60):
        # -- the player's acts (a mixed, mostly decent player)
        for _ in range(rng.choice([0, 1, 1, 2])):
            verb = rng.choices(list(VERBS), weights=[5, 3, 0.4, 1.5, 1.5, 0.6, 1, 0])[0]
            # players deal mostly with the same few people (their circle), sometimes a stranger
            patient = rng.choice(circle) if rng.random() < 0.8 else rng.randrange(n)
            e = {"id": len(log), "day": day, "actor": "PLAYER", "verb": verb, "patient": patient,
                 "weight": VERBS[verb][2], "witnesses": [patient] + rng.sample(range(n), 2)}
            log.append(e)
            full = pp.eager(seed, e, people, adj)
            full.pop(pp.PUBLIC, None)
            known[e["id"]] = {x: (t, h) for x, (t, h, _) in full.items()}
            counts[(patient, verb)] = counts.get((patient, verb), 0) + 1
            # -- story sifting: patterns over the log (a few of the catalogue's types)
            if verb == "rescue":
                open_arc("rescue", day, {"rescuer": "PLAYER", "unfortunate": patient}, "the player pulled someone from danger")
            if verb in ("help", "gift", "return_lost") and counts.get((patient, "help"), 0) + counts.get((patient, "gift"), 0) >= 2 \
                    and not any(a.id == "friendship" and a.roles["friend_b"] == patient for a in arcs + done + background):
                open_arc("friendship", day, {"friend_a": "PLAYER", "friend_b": patient}, "repeated kindness to the same person", key=("friend", patient))
            if verb == "return_lost":
                open_arc("lost_and_found", day, {"finder": "PLAYER", "loser": patient}, "a lost thing returned")
            if verb in ("steal", "insult", "break_promise"):
                # the avenger: the victim's closest tie with low agreeableness (or the victim)
                cands = [patient] + [v for v, l in ties[patient].items() if l <= 15]
                av = min(cands, key=lambda c: people[c]["A"])
                if people[av]["A"] < 0.45 or verb == "steal":
                    a = open_arc("vengeance", day, {"avenger": av, "criminal": "PLAYER", "victim": patient},
                                 "the player %s %d" % (verb.replace("_", " "), patient), key=("avenge", av))
                    a.events = getattr(a, "events", []) + [e]
            if verb == "apologize":
                for a in arcs + background:
                    if a.id == "vengeance" and patient in (a.roles["victim"], a.roles["avenger"]) and a.outcome is None:
                        a.outcome = "comedy"          # forgiveness: the enemies leave as friends (Frye)
                        a.log.append((day, "apology -> forgiveness"))
        # -- a world event: the air plant fails; no actor; stress looks for a face
        if day == crisis_day:
            open_arc("community_crisis", day, {"community": "settlement", "threat": "air plant"}, "the air plant failed")
            low = [x for x in range(n) if opinion(x, day) < -0.5]
            if len(low) >= 6:
                open_arc("scapegoat", day, {"scapegoat": "PLAYER", "crowd": len(low)},
                         "%d residents already think ill of the newcomer" % len(low))
        # -- rumour: a player misdeed known to >= 12% of the settlement
        for e in log:
            if e["actor"] == "PLAYER" and VERBS[e["verb"]][0] < 0 and not e.get("rumour"):
                share = sum(1 for x in known[e["id"]] if know(x, e, day)) / n
                if share >= 0.12:
                    e["rumour"] = True
                    open_arc("rumour_run_wild", day, {"subject_of_rumour": "PLAYER"},
                             "word of the %s (event %d) reached %.0f%%" % (e["verb"], e["id"], 100 * share), key=("rumour", "PLAYER"))
        # -- world-triggered beats: they happen when the world makes them true (no drama manager needed)
        for a in arcs + background:
            if a.outcome is not None:
                continue
            nb = a.t["beats"][min(a.beat + 1, len(a.t["beats"]) - 1)]["beat"]
            if a.id == "vengeance" and nb == "learning" and any(know(a.roles["avenger"], ev, day) for ev in a.events):
                a.advance(day)
            elif a.id == "vengeance" and nb == "vow" and opinion(a.roles["avenger"], day) < -0.8:
                a.advance(day)
            elif a.id == "friendship" and nb == "sho" and counts.get((a.roles["friend_b"], "help"), 0) + counts.get((a.roles["friend_b"], "gift"), 0) >= 3:
                a.advance(day)
            # untended arcs fade: nothing for 20 days -> forgotten (an ironic non-ending)
            if day - a.log[-1][0] > 20 and a.beat < len(a.t["beats"]) - 1:
                a.outcome = "faded"
            # a background arc gets promoted when a featured slot frees up
        while len([x for x in arcs if x.outcome is None]) < MAX_FEATURED and background:
            loud_n = len([x for x in arcs if x.outcome is None and not quiet(x)])
            pool = [b for b in background if b.outcome is None and (quiet(b) or loud_n < MAX_FEATURED - QUIET_SLOTS)]
            cand = max(pool, key=lambda b: b.quality, default=None)
            if cand is None:
                break
            background.remove(cand)
            arcs.append(cand)
        # -- the drama manager: surface the beat that moves tension toward the storyteller's target
        target = STORYTELLERS[teller](day)
        live = [a for a in arcs if a.outcome is None]
        now = 0.1                                       # nothing surfaced today: calm
        if live:
            best = min(live, key=lambda a: abs(a.next_tension() - target) + 0.02 * (day - a.log[-1][0] < 2))
            # quiet arcs can always step; conflict arcs step only when the target is high enough
            if best.next_tension() <= target + 0.25:
                if best.advance(day):
                    best.outcome = best.outcome or resolve(best, day)
                now = best.tension()
            else:
                now = 0.1
        tension_hist.append((day, target, now))
        for lst in (arcs, background):
            for a in list(lst):
                if a.outcome is not None:
                    lst.remove(a)
                    done.append(a)
        opinion_hist.append(sum(opinion(x, day) for x in range(0, n, 7)) / len(range(0, n, 7)))

    # -- report
    ended = [a for a in done if a.outcome != "faded"]
    print("storyteller: %s; %d player acts; arcs sifted %d (merged into existing: %d); featured-or-finished %d; "
          "faded untended %d; still in background %d" % (teller, len(log), len(done) + len(arcs) + len(background) + merged[0],
          merged[0], len(ended) + len(arcs), len(done) - len(ended), len(background)))
    print("\nTHE PLAYER'S HISTORY, AS ARCS (featured and finished)")
    for a in sorted(ended + arcs, key=lambda a: a.day):
        beats = " > ".join("%s@%d" % (b, d) for d, b in a.log)
        print("  day %2d  %-18s %-10s %s\n          why: %s\n          beats: %s" % (
            a.day, a.id, a.outcome or "(live)", " ".join("%s=%s" % kv for kv in a.roles.items()), a.why, beats))
    print("\ntension (target / surfaced) every 5 days:")
    print("  " + "  ".join("%d:%.2f/%.2f" % t for t in tension_hist[::5]))
    print("mean opinion of the player, every 10 days: " + "  ".join("%.2f" % o for o in opinion_hist[::10]))
    live = [a for a in arcs if a.outcome is None] or done[-1:]
    if live:
        a = live[0]
        b = a.t["beats"][min(a.beat, len(a.t["beats"]) - 1)]
        role, who = next(((r, w) for r, w in a.roles.items() if w != "PLAYER" and isinstance(w, int)), (None, None))
        print("\n[STORY] card for resident %s (role '%s' in '%s'):" % (who, role, a.t["name"]))
        print("  ST.type=%s  ST.role=%s (%s)  ST.beat=%s  ST.stage=%s  ST.tension=%.2f  ST.value=%s  ST.theme=\"%s\"" % (
            a.id, role, next((r["actant"] for r in a.t["roles"] if r["role"] == role), "?"), b["beat"], b["stage"],
            b["tension"], a.t["value"], a.t["theme"]))
        print("  beat function: %s" % b["function"])


if __name__ == "__main__":
    main()
