#!/usr/bin/env python3
"""Build the Columbia game bible: validate the canon and write it out for the engine and for reading.

    python3 tools/bible/make_bible.py            # names (make_names) + canon -> JSON + docs

Writes godot_project/remake/bible/*.json (the engine's data; see schema.json) and research/bible/*.md
(the same, to read). Fails loudly on any broken cross-reference: people named in events, lineages,
places, story types, roles, occupations, faiths, surnames.

Generated (deterministic, flagged 'generated'): the Moderators of the unnamed terms, the Spin Cup
winners of the unnamed years, the minor lineages of notable people, the 'heroes' given-name pool.
"""
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import canon_culture as CU
import canon_earth as EA
import canon_future as FU
import canon_history as HI
import canon_lineages as LI
import canon_people as PE
import canon_world as WO
import make_names

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
OUT = os.path.join(ROOT, "godot_project", "remake", "bible")
DOCS = os.path.join(ROOT, "research", "bible")
LAUNCH = WO.LAUNCH_AD
errors = []


def err(msg):
    errors.append(msg)


def h01(*parts):
    return int.from_bytes(hashlib.blake2b("|".join(map(str, parts)).encode(), digest_size=8).digest(), "little") / 2 ** 64


def pick(weights, *key):
    tot = sum(weights.values())
    r = h01(*key) * tot
    for k, w in weights.items():
        r -= w
        if r <= 0:
            return k
    return k


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(DOCS, exist_ok=True)
    names, name_stats = make_names.build()
    occ = json.load(open(os.path.join(ROOT, "godot_project", "remake", "characters", "npc_traits.json")))["tables"]["occupations"]
    roles = {r["id"] for r in json.load(open(os.path.join(ROOT, "research", "roles", "roles.json")))["roles"]}
    stories = {s["id"] for s in json.load(open(os.path.join(ROOT, "research", "story", "story_types.json")))["story_types"]}
    place_types = set(json.load(open(os.path.join(ROOT, "godot_project", "remake", "characters", "npc_places.json")))["types"]) | {"charge_stop"}
    settlements = {s["id"]: s for s in WO.SETTLEMENTS}
    regions = {r["id"] for r in WO.WORLD["geography"]["regions"]}
    faiths = {f["id"] for f in WO.WORLD["faiths_2752"]}
    where_ok = set(settlements) | regions | {"station", "undercroft", "earth", "kettle_valley", "north_shore", "south_shore"}
    surname_rows = {r[0].lower(): r for r in names["surnames"]}
    extinct = {r[0].lower() for r in names["extinct_founding_surnames"]}
    heritages = set(names["surname_heritage_share_2752"]) | {"black", "african", "francophone", "anglo"}

    # -- events --------------------------------------------------------------------------------------
    people = {p["id"]: p for p in PE.PEOPLE}
    if len(people) != len(PE.PEOPLE):
        err("duplicate person ids")
    events = []
    for e in EA.EARTH_EVENTS:
        x = dict(e)
        x["vy"] = x.pop("ad") - LAUNCH
        x["end_vy"] = (x.pop("end") - LAUNCH) if x.get("end") is not None else None
        x["ad"] = x["vy"] + LAUNCH
        x["era"] = "prelude_earth" if x["vy"] < 0 else era_of(x["vy"])
        x["scope"] = "earth"
        events.append(x)
    for e in HI.EVENTS:
        x = dict(e)
        x["ad"] = x["vy"] + LAUNCH
        x["era"] = era_of(x["vy"])
        x["scope"] = "station"
        events.append(x)
    ev_ids = Counter(e["id"] for e in events)
    for k, n in ev_ids.items():
        if n > 1:
            err("duplicate event id %s" % k)
    evs = {e["id"]: e for e in events}
    for e in events:
        for p in e["people"]:
            if p not in people:
                err("event %s: unknown person %s" % (e["id"], p))
        for w in e["where"]:
            if w not in where_ok:
                err("event %s: unknown place %s" % (e["id"], w))
        for s in e["story_types"]:
            if s not in stories:
                err("event %s: unknown story type %s" % (e["id"], s))
        if e["known"] not in WO.WORLD["knowledge_levels"]:
            err("event %s: unknown knowledge level %s" % (e["id"], e["known"]))
    events.sort(key=lambda e: (e["vy"], e["id"]))

    # -- people ----------------------------------------------------------------------------------------
    lineage_ids = {l["id"] for l in LI.LINEAGES}
    minor = {}
    for p in PE.PEOPLE:
        if p["occupation"] is not None and p["occupation"] not in occ:
            err("person %s: occupation %s" % (p["id"], p["occupation"]))
        if p["faith"] not in faiths:
            err("person %s: faith %s" % (p["id"], p["faith"]))
        if p["home"] not in settlements and p["home"] != "earth":
            err("person %s: home %s" % (p["id"], p["home"]))
        bp = p["birthplace"]
        if not (bp.startswith("earth:") or bp in settlements):
            err("person %s: birthplace %s" % (p["id"], bp))
        for m in p["moved_to"]:
            if m not in settlements:
                err("person %s: moved_to %s" % (p["id"], m))
        for d in p["deeds"]:
            if d not in evs:
                err("person %s: deed %s" % (p["id"], d))
        for r in p["roles"]:
            if r not in roles:
                err("person %s: role %s" % (p["id"], r))
        if p["children"] == 0 and not p["childless"]:
            err("person %s: childless reason missing" % p["id"])
        dv = p["died_vy"]
        alive = dv is None
        age = 500 - p["born_vy"] if alive else None
        if alive and not (0 <= age <= 110):
            err("person %s: living age %s" % (p["id"], age))
        if isinstance(dv, int) and dv < p["born_vy"]:
            err("person %s: died before born" % p["id"])
        p["alive"] = alive
        p["missing"] = dv == "missing"
        p["age_vy500"] = age
        p["born_ad"] = p["born_vy"] + LAUNCH
        p["died_ad"] = dv + LAUNCH if isinstance(dv, int) else None
        p["native"] = p["origin"] in ("station", "bank")
        p["immigrant"] = p["origin"] == "founder"
        p["internal_migrant"] = bool(p["moved_to"])
        for part in p["surname"].split("-"):
            key = part.lower().replace("ñ", "n")
            if key not in surname_rows and part.lower() not in surname_rows and key not in extinct and part.lower() not in extinct:
                names["surnames"].append([part, 25, "lineage_kept", 1, 5, 12])     # a notable line kept alive in the catalogue
                surname_rows[part.lower()] = names["surnames"][-1]
        for lid in p["lineages"]:
            if lid not in lineage_ids and lid not in minor:
                sn = next((s for s in p["surname"].split("-") if s.lower().replace("ñ", "n").replace("á", "a") == lid.replace("_", "")), None) or lid.title()
                minor[lid] = dict(id=lid, surname=sn, founder=None, origin=bp if p["origin"] == "founder" else "station", heritage=surname_heritage(sn, surname_rows),
                                  strongholds={p["home"]: 1} if p["home"] in settlements else {}, trades=[p["occupation"]] if p["occupation"] else [], faith=p["faith"],
                                  tilt={}, known_for=[p["title"]] if p["title"] else [], lore=[], members=[], feuds=[], allies=[], status="thriving", reputation="respected",
                                  minor=True, generated=True)
            if lid in minor:
                minor[lid]["members"].append(p["id"])
    for a, b, rel in PE.KIN:
        if a not in people or b not in people:
            err("kin: unknown %s/%s" % (a, b))

    # -- lineages ------------------------------------------------------------------------------------
    for key, n in LI.BEARERS_2752.items():
        row = surname_rows.get(key)
        if row is None:                     # extinct in the simulation, alive in the canon: restore it
            lin_ = next((l for l in LI.LINEAGES if l["id"] == key), None)
            row = [lin_["surname"] if lin_ else key.title(), n, surname_heritage_of_lineage(key), 1, max(1, n // 20), max(1, n // 4)]
            names["surnames"].append(row)
            surname_rows[key] = row
        row[1] = n
        if row[2] == "lineage_kept":
            row[2] = surname_heritage_of_lineage(key)
    names["surnames"].sort(key=lambda r: -r[1])
    lineages = []
    for l in LI.LINEAGES:
        x = dict(l)
        x["minor"] = False
        x["feuds"] = [dict(with_=f[0], value=f[1], why=f[2]) for f in l["feuds"]]
        for f in x["feuds"]:
            f["with"] = f.pop("with_")
        if x["founder"] and x["founder"] not in people:
            err("lineage %s: founder %s" % (x["id"], x["founder"]))
        for m in x["members"]:
            if m not in people:
                err("lineage %s: member %s" % (x["id"], m))
        for s in x["strongholds"]:
            if s not in settlements:
                err("lineage %s: stronghold %s" % (x["id"], s))
        if x["faith"] not in faiths:
            err("lineage %s: faith %s" % (x["id"], x["faith"]))
        row = surname_rows.get(x["surname"].lower())
        x["bearers_2752"] = row[1] if row else 0
        lineages.append(x)
    lids = {l["id"] for l in lineages} | set(minor)
    for l in lineages:
        for f in l["feuds"]:
            if f["with"] not in lids:
                err("lineage %s: feud with %s" % (l["id"], f["with"]))
        for a in l["allies"]:
            if a not in lids:
                err("lineage %s: ally %s" % (l["id"], a))
    for m in minor.values():
        row = surname_rows.get(m["surname"].lower())
        m["bearers_2752"] = row[1] if row else 0
    lineages += sorted(minor.values(), key=lambda m: m["id"])
    import unicodedata
    for l in lineages:                       # the lookup key: lower case, accents folded (Nuñez = Nunez)
        l["key"] = "".join(c for c in unicodedata.normalize("NFKD", l["surname"].lower()) if not unicodedata.combining(c))

    # -- factions ----------------------------------------------------------------------------------
    fids = {f["id"] for f in LI.FACTIONS}
    for f in LI.FACTIONS:
        for s in f["strong_in"]:
            if s not in settlements:
                err("faction %s: %s" % (f["id"], s))
        for p in f["leaders"]:
            if p not in people:
                err("faction %s: leader %s" % (f["id"], p))
    for a, b, v in LI.FACTION_AFFINITY:
        if a not in fids or b not in fids:
            err("faction affinity %s/%s" % (a, b))
    for a, b, v in LI.FAITH_AFFINITY:
        if a not in faiths or b not in faiths:
            err("faith affinity %s/%s" % (a, b))
    for s in WO.SETTLEMENTS:
        for r in s["rivals"] + s["allies"]:
            if r not in settlements:
                err("settlement %s: %s" % (s["id"], r))
        for k in s["faith_lean"]:
            if k not in faiths:
                err("settlement %s: faith %s" % (s["id"], k))
        for k in s["heritage_lean"]:
            if k not in heritages:
                err("settlement %s: heritage %s" % (s["id"], k))
        if s["named_for"] in people or s["named_for"] in ("lake_tamsin",):
            pass

    # -- culture ------------------------------------------------------------------------------------
    for h in CU.HOLIDAYS:
        for pl in h[8]:
            if pl not in place_types:
                err("holiday %s: place %s" % (h[0], pl))
    for f in CU.FOODS:
        for pl in f[5]:
            if pl not in place_types:
                err("food %s: place %s" % (f[0], pl))
    for r in CU.RITES:
        for pl in r[5]:
            if pl not in place_types:
                err("rite %s: place %s" % (r[0], pl))

    # -- generated: Moderators, Spin Cups, the heroes pool -----------------------------------------------
    mods = []
    given_by_cohort = cohort_names(names)
    for start, pid in HI.MODERATORS:
        if pid and pid not in people:
            err("moderator %s" % pid)
        if pid:
            p = people[pid]
            mods.append(dict(term=[start, start + 4], person=pid, name="%s %s" % (p["given"], p["surname"]), generated=False))
        else:
            sex = "F" if h01("mod", start) < 0.5 else "M"
            born = start - 45 - int(h01("modage", start) * 20)
            g = pick_name(given_by_cohort, born + LAUNCH, sex, ("modg", start))
            snap = 4 if start < 150 else 5
            sn = pick_surname(names, snap, ("mods", start))
            town = pick({s["id"]: s["pop"] for s in WO.SETTLEMENTS if s["id"] != "countryside" and s["founded_vy"] <= start}, "modtown", start)
            mods.append(dict(term=[start, start + 4], person=None, name="%s %s" % (g, sn), sex=sex, born_vy=born, home=town, generated=True))
    cups = []
    strength = {t: 1.0 for t in HI.TEAMS}
    for y in range(201, 500):
        if y in HI.SPIN_CUP_FIXED:
            w = HI.SPIN_CUP_FIXED[y]
            gen = False
        else:
            wts = dict(strength)
            for t, (_, town) in HI.TEAMS.items():
                wts[t] *= settlements[town]["pop"] / 10000.0 + 0.6
                if t == "port_carrow_mariners" and 340 <= y <= 355:
                    wts[t] *= 6
                if t == "solana_point_suns" and y >= 460:
                    wts[t] *= 2.5
                if t in ("tern_harbor_netters", "pelican_cove_canners") and 320 <= y <= 400:
                    wts[t] *= 2
            w = pick(wts, "cup", y)
            gen = True
        if w not in HI.TEAMS:
            err("cup team %s" % w)
        cups.append(dict(vy=y, ad=y + LAUNCH, winner=w, team=HI.TEAMS[w][0], generated=gen))
    heroes = {"F": Counter(), "M": Counter()}
    for p in PE.PEOPLE:
        if p["origin"] != "earth_side" and p["fame"] >= 0.25:
            heroes[p["sex"]][p["given"]] += p["fame"]
    names["given_pools"]["heroes"] = {s: [[n, round(v / sum(c.values()) * 1e6, 1)] for n, v in c.most_common()] for s, c in heroes.items()}

    if errors:
        print("\n".join("ERROR " + e for e in errors))
        sys.exit(1)

    # -- write ------------------------------------------------------------------------------------------
    world = dict(WO.WORLD)
    world["present"] = {"ad": WO.PRESENT_AD, "vy": WO.PRESENT_VY, "date": WO.WORLD["calendar"]["present_date"]}
    history = {"eras": HI.ERAS, "future_eras": FU.FUTURE_ERAS, "events": events, "future_events": [dict(f, ad=f["vy"] + LAUNCH, known="lost") for f in FU.FUTURE_EVENTS],
               "moderators": mods, "spin_cup": cups, "teams": {k: {"name": v[0], "town": v[1]} for k, v in HI.TEAMS.items()}}
    peo = {"people": PE.PEOPLE, "kin": [dict(a=a, b=b, rel=r) for a, b, r in PE.KIN]}
    lin = {"lineages": lineages}
    fac = {"factions": LI.FACTIONS, "faction_affinity": [dict(a=a, b=b, value=v) for a, b, v in LI.FACTION_AFFINITY],
           "region_affinity": [dict(a=a, b=b, value=v) for a, b, v in LI.REGION_AFFINITY], "settlement_rivalry": LI.SETTLEMENT_RIVALRY,
           "settlement_alliance": LI.SETTLEMENT_ALLIANCE, "faith_affinity": [dict(a=a, b=b, value=v) for a, b, v in LI.FAITH_AFFINITY]}
    cul = {"holidays": [dict(zip(("id", "name", "date", "origin", "since_vy", "observed_by", "share", "activities", "places", "foods", "notes"), h)) for h in CU.HOLIDAYS],
           "foods": [dict(zip(("id", "name", "kind", "origin", "when", "places", "notes"), f)) for f in CU.FOODS],
           "rites": [dict(zip(("id", "name", "stage", "what", "origin", "places"), r)) for r in CU.RITES],
           "customs": [dict(zip(("id", "name", "what"), c)) for c in CU.CUSTOMS],
           "lexicon": [dict(zip(("term", "meaning", "origin", "who", "example"), l)) for l in CU.LEXICON],
           "sayings": [dict(zip(("saying", "use"), s)) for s in CU.SAYINGS],
           "beliefs": [dict(zip(("id", "belief", "share", "source", "held_by"), b)) for b in CU.BELIEFS],
           "superstitions": [dict(zip(("id", "what"), s)) for s in CU.SUPERSTITIONS],
           "etiquette": [dict(zip(("id", "what"), s)) for s in CU.ETIQUETTE],
           "taboos": [dict(zip(("id", "what", "strength"), s)) for s in CU.TABOOS],
           "pastimes": [dict(zip(("id", "name", "kind", "what", "share"), s)) for s in CU.PASTIMES],
           "arts": [dict(zip(("id", "name", "kind", "what"), s)) for s in CU.ARTS],
           "dialect": CU.DIALECT, "changes": [dict(zip(("id", "origin", "now", "why"), c)) for c in CU.CHANGES], "schooling": CU.SCHOOLING}
    files = {"world": world, "settlements": {"settlements": WO.SETTLEMENTS}, "history": history, "people": peo, "lineages": lin,
             "factions": fac, "culture": cul, "names": names, "schema": SCHEMA}
    for k, v in files.items():
        v = dict(v)
        v.setdefault("_about", "Columbia game bible: %s. Generated by tools/bible/make_bible.py from tools/bible/canon_*.py; read research/bible/." % k)
        with open(os.path.join(OUT, k + ".json"), "w") as f:
            json.dump(v, f, ensure_ascii=False, indent=None if k == "names" else 1, separators=(",", ":") if k == "names" else None)
    counts = {"events_past": len(events), "events_future": len(FU.FUTURE_EVENTS), "eras": len(HI.ERAS) + len(FU.FUTURE_ERAS), "people": len(PE.PEOPLE),
              "people_living": sum(1 for p in PE.PEOPLE if p["alive"]), "lineages_major": len(LI.LINEAGES), "lineages_minor": len(minor),
              "factions": len(LI.FACTIONS), "settlements": len(WO.SETTLEMENTS), "holidays": len(CU.HOLIDAYS), "foods": len(CU.FOODS), "lexicon": len(CU.LEXICON),
              "beliefs": len(CU.BELIEFS), "moderators": len(mods), "spin_cups": len(cups), "surnames_2752": len(names["surnames"]),
              "extinct_surnames_listed": len(names["extinct_founding_surnames"]),
              "given_names": sum(len(v[s]) for v in names["given_pools"].values() for s in v)}
    with open(os.path.join(OUT, "index.json"), "w") as f:
        json.dump({"_about": "Columbia game bible manifest", "version": 1, "files": sorted(k + ".json" for k in files), "counts": counts, "name_stats": name_stats},
                  f, ensure_ascii=False, indent=1)
    import make_docs
    make_docs.write(DOCS, world, WO.SETTLEMENTS, history, peo, lin, fac, cul, names, counts, name_stats)
    print(json.dumps(counts, indent=1))


def era_of(vy):
    for e in HI.ERAS:
        if e["vy"][0] <= vy < e["vy"][1]:
            return e["id"]
    return "the_present_age" if vy >= 420 else "prelude_earth"


def surname_heritage_of_lineage(key):
    l = next((l for l in LI.LINEAGES if l["id"] == key), None)
    return l["heritage"] if l else "anglo"


def surname_heritage(sn, rows):
    r = rows.get(sn.lower())
    return r[2] if r else "anglo"


def cohort_names(names):
    return names


def pick_name(names, birth_ad, sex, key):
    coh = next((c for c in names["cohorts"] if c["from"] <= birth_ad <= c["to"]), names["cohorts"][0])
    mix = {k: v for k, v in coh["mix"].items() if k not in ("heritage", "vogue", "heroes")}
    pool = pick(mix, *key, "pool")
    lst = names["given_pools"][pool][sex][:300]
    return pick({n: w for n, w, *rest in lst}, *key, "name")


def pick_surname(names, col, key):
    return pick({r[0]: max(0.1, r[col]) for r in names["surnames"][:2500]}, *key)


SCHEMA = {
    "_about": "Field vocabularies of the Columbia game bible (tokens the engine can rely on).",
    "event.kind": ["founding", "law", "political", "birth", "death", "disaster", "epidemic", "migration", "economy", "sport", "faith", "culture", "science",
                   "construction", "contact", "conflict", "crime", "mystery", "festival", "milestone", "present", "discovery"],
    "event.known": ["living", "family", "schooled", "ritual", "place", "legend", "scholar", "lost"],
    "event.effects": "prefix:value tokens -- pop:<n> (population change), holiday:<id>, place:<id> (a name given), name:<given>+ (a name's popularity), culture:<axis><+|->, "
                     "institution:<id>, law:<id>, faith:<id><+>, faction:<id><+>, custom:<id>, tech:<id>, climate:<id>, economy:<id>, migration:<from>_to_<to>, "
                     "cohort:<id>, mystery:<id>, rivalry:<a>-<b><+>, media:<id>, wildlife:<id>, genetics:<id>, calendar:<id>, politics:<id>",
    "person.origin": ["earth_side", "founder", "station", "bank"],
    "person.marital": ["married", "widowed", "divorced", "never_married", "partnered"],
    "person.childless": ["gave_share", "vocation", "chose_not", "infertility", "died_young", "partner_died", "duty", "protest", "share_lapsed", "unknown"],
    "person.reputation": ["revered", "hero", "beloved", "respected", "contested", "notorious", "villain", "forgotten", "private"],
    "person.traits": "psychology tokens: P.<facet>:<very_low|low|moderate|high|very_high>, V.<value>, D.<dark trait>:<level>, speech:<style>",
    "lineage.status": ["thriving", "dwindled", "extinct_by_name"],
    "faction.kind": ["political", "guild", "club", "faith", "society", "fans", "heritage", "institution"],
    "culture.era_axes": ["tight", "individualism", "trust_institutions", "faith", "optimism", "earth_mindedness", "curiosity_about_voyage"],
    "names.pool": ["earth_old", "earth_mid", "earth_new", "heritage_<h>", "station", "heroes", "vogue:<decade>"],
    "names.heritage": ["anglo", "german", "irish_scots", "italian", "polish", "hungarian", "slavic", "greek", "dutch", "scandinavian", "francophone", "hispanic",
                       "black", "black_anglo", "african", "arab", "south_asian", "east_asian", "se_asian", "indigenous", "multi", "station_coined", "lineage_kept"],
}

if __name__ == "__main__":
    main()
