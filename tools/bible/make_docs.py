"""Write research/bible/*.md from the same data make_bible.py writes as JSON (called by make_bible)."""
import os


def md_table(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in r) + " |")
    return out


def w(path, lines):
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def write(D, world, settlements, history, peo, lin, fac, cul, names, counts, name_stats):
    people = {p["id"]: p for p in peo["people"]}
    nm = lambda pid: "%s %s" % (people[pid]["given"], people[pid]["surname"]) if pid in people else pid

    # README ------------------------------------------------------------------------------------------
    w(os.path.join(D, "README.md"), [
        "# The Columbia game bible",
        "",
        "The canon of Space Station Columbia as **data for the procedural engine**: names, history, people, families, factions, culture, places and the outside world.",
        "It is built from `tools/bible/canon_*.py` and the downloaded name data by `tools/bible/make_bible.py`, which checks every cross-reference.",
        "The build writes the engine files to `godot_project/remake/bible/*.json` and these pages.",
        "",
        "**The premise (the user, 2026-09-30):**",
        "- Columbia is an ark ship on a 1,500-year voyage to another star, launched from Earth in 2252.",
        "- It is a self-contained, balanced world.",
        "- The game is set 500 years after launch (VY 500, 2752). People only vaguely know why they are aboard or where they are going.",
        "- The founders came from the southern Great Lakes and reflect the diversity of the whole continent.",
        "- 250,000 people live aboard (the test towns hold a small sample).",
        "- The station lasts 3,000 years.",
        "- Every vehicle is electric or pedal-powered, and trams run on roads.",
        "- The player is from somewhere else aboard. The user chooses where.",
        "",
        "## Contents",
        "| page | engine file | what |",
        "|---|---|---|",
        "| [01_world.md](01_world.md) | world.json | the ship, the voyage, the Steward, the calendar, the land, the population, the institutions, faiths, languages, what people know |",
        "| [02_names.md](02_names.md) | names.json | %d surnames alive in 2752 (from %d founding surnames), given-name pools and the cohort mixes, nicknames |" % (counts["surnames_2752"], name_stats["founding_surnames"]),
        "| [03_history.md](03_history.md) | history.json | %d eras, %d past events (year by year in living memory), %d future events, every Moderator, every Spin Cup |" % (counts["eras"], counts["events_past"], counts["events_future"]),
        "| [04_people.md](04_people.md) | people.json | %d important people (%d living): native or immigrant, marriages, children or why not, deeds, reputation |" % (counts["people"], counts["people_living"]),
        "| [05_lineages.md](05_lineages.md) | lineages.json | %d great families and %d minor lines: trades, faith, temperament, lore, feuds and alliances |" % (counts["lineages_major"], counts["lineages_minor"]),
        "| [06_culture.md](06_culture.md) | culture.json | holidays, foods, rites, customs, the lexicon, sayings, beliefs, superstitions, etiquette, taboos, pastimes, arts, dialect, and what changed from Earth |",
        "| [07_settlements.md](07_settlements.md) | settlements.json | the 21 towns at full scale: population, founding, character, districts, heritage and faith leanings, landmarks, rivals |",
        "| [08_outside_world.md](08_outside_world.md) | history.json (scope earth) | Earth before the launch, the Earth-link, the other arks, the destination, the future |",
        "| [09_affinity.md](09_affinity.md) | factions.json | factions and the **affinity model**: priors between people and toward the player, and what's stored |",
        "| [10_engine.md](10_engine.md) | schema.json, index.json | how the engine uses each file |",
        "| [12_industry.md](12_industry.md) | industry.json | the Rock and the Spindle, the Drops, what the Steward makes and the limits it keeps (the Thirty-Two, panels, gauges, the Wire slot), the boards, how things are made, the three vehicle works and their histories |",
        "",
        "## Sources",
        "- **Surnames:** the 2000 US Census surname file (151,671 names, with ethnic shares), via fivethirtyeight/data.",
        "- **Given names:** SSA baby names 1880-2017 (every name given to 5 or more births in a year), via hadley/babynames.",
        "  The census.gov and ssa.gov servers refuse scripted downloads, so the files come from GitHub mirrors. The raw files are in the gitignored `reference/names/`.",
        "- **The project's own research:**",
        "  - `research/demographics` (Great Lakes community profiles);",
        "  - `research/psychology/03_frontier_and_space.md` (frontier and isolated-environment psychology);",
        "  - `research/roles` (roles in middle America and aboard stations);",
        "  - `research/story` (story types);",
        "  - `research/coastal_communities` (the towns' real-world models).",
        "- **Generation ships:** Moore 2002/2003 (a crew of about 160, or 80 with delayed childbearing, for 200 years); Smith 2014 (tens of thousands, allowing for catastrophes); Marin & Beluffi 2018 (a minimal crew for Proxima b); Project Hyperion (i4is; 2024-25 competition won by *Chrysalis*). All via Wikipedia, *Generation ship*.",
        "- **Destination:** Alpha Centauri at 4.34 ly; A is a G2V star at 1.51 times the Sun's luminosity, with a habitable zone of about 0.9-1.5 AU (Wikipedia, *Alpha Centauri*). **Hesper is fiction.**",
        "- **Habitat form:** O'Neill's cylinders (*The High Frontier*, 1976; NASA SP-413, 1977).",
        "- **Collective memory:** Jan Assmann's communicative memory (about 80-100 years, three generations) and Jan Vansina's 'floating gap' (*Oral Tradition as History*, 1985). **From knowledge:** the Wikipedia pages fetched didn't carry these details.",
        "- **Great Lakes communities:** Polish (Chicago, Detroit/Hamtramck, Buffalo's Dyngus Day, Milwaukee), Hungarian (Cleveland's Buckeye Road, Toledo's Birmingham) and Arab (Dearborn) communities, via Wikipedia.",
        "- **Inland North dialect:** 'pop', 'party store', 'doorwall', 'gapers' block', 'bubbler', and the Northern Cities Vowel Shift (Wikipedia, *Inland Northern American English*).",
        "- **Knowledge, not fetched:**",
        "  - Quebec surnames and the heritage given-name lists;",
        "  - the founders' ancestry mix (a canon extrapolation, not a forecast);",
        "  - the Indigenous given names, which **must be reviewed with community sources**.",
    ])

    # 01 world -----------------------------------------------------------------------------------------
    s = world["ship"]
    v = world["voyage"]
    L = ["# 1. The world", "", "## The ship"]
    L += md_table([(k, s[k]) for k in s], ["", ""])
    L += ["", "## The voyage"] + md_table([(k, v[k]) for k in v if k != "destination_facts" and k != "phases"], ["", ""])
    L += ["", "**Destination:** " + "; ".join("%s: %s" % kv for kv in v["destination_facts"].items())]
    L += ["", "**Phases:** " + ", ".join("%s VY %d-%d" % (p["id"], p["vy"][0], p["vy"][1]) for p in v["phases"])]
    L += ["", "## The Steward", "", "- **What it does:** " + ", ".join(world["steward"]["does"]), "- **Tenders:** " + world["steward"]["tenders"],
          "- **Speaking:** " + world["steward"]["speaks"], "- **What people think:** " + "; ".join(world["steward"]["people_think"])]
    L += ["", "## The calendar", ""] + ["- **%s:** %s" % (k, v2 if not isinstance(v2, dict) else "; ".join("%s %s" % kv for kv in v2.items())) for k, v2 in world["calendar"].items()]
    g = world["geography"]
    L += ["", "## The land", "", "**Directions:** " + "; ".join("%s = %s" % kv for kv in g["directions"].items()), "",
          "**Regions:** " + "; ".join("%s (%s)" % (r["name"], r["what"]) for r in g["regions"]), "",
          "**Waters:** " + "; ".join("%s: %s" % (x.get("name", "creeks"), x.get("what", ", ".join(x.get("names", [])))) for x in g["waters"]), "",
          "**Rail:** " + g["rail"], "", "**Wildlife:** " + g["wildlife"], "", "**Livestock:** " + g["livestock"]]
    pop = world["population"]
    L += ["", "## Population", "", "- launch %d (crew %d); the Balance %d (reached VY %d); the census of VY %d: %d" % (pop["launch"], pop["launch_crew"], pop["balance"], pop["balance_reached_vy"], pop["present_census_vy"], pop["present_census"]),
          "- curve (VY, people): " + ", ".join("%d: %d" % tuple(c) for c in pop["curve"]),
          "- age structure 2752: " + ", ".join("%s %d%%" % (k, round(v2 * 100)) for k, v2 in pop["age_structure_2752"].items()),
          "- life expectancy %.1f; about %d births and %d deaths a year" % (pop["life_expectancy_2752"], pop["births_per_year"], pop["deaths_per_year"])]
    L += ["", "## Institutions", ""]
    for k, x in world["institutions"].items():
        L.append("- **%s:** %s" % (x.get("name", k), "; ".join("%s: %s" % (a, b if not isinstance(b, list) else ", ".join(map(str, b))) for a, b in x.items() if a != "name")))
    L += ["", "## Faiths (2752)", ""] + md_table([(f["name"], "%d%%" % round(f["share"] * 100)) for f in world["faiths_2752"]], ["faith", "share"])
    L += ["", "## Languages", ""] + ["- **%s:** %s" % (l["name"], "; ".join("%s %s" % (k, v2) for k, v2 in l.items() if k not in ("id", "name"))) for l in world["languages_2752"]]
    L += ["", "## What people know: the knowledge levels", ""] + ["- **%s:** %s" % kv for kv in world["knowledge_levels"].items() if kv[0] != "_about"]
    L += ["", "**Memory model:** " + world["memory_model"]]
    w(os.path.join(D, "01_world.md"), L)

    # 02 names -------------------------------------------------------------------------------------------
    L = ["# 2. Names", "", "Generated by `tools/bible/make_names.py`: the method is in its docstring and summarised here.", "",
         "## Surnames",
         "- **Founders:** 72,000 founders were drawn from the 2000 Census surname file, reweighted to the founders' ancestry mix: %s." % ", ".join("%s %d%%" % (k, round(v2 * 100)) for k, v2 in names["method"]["founder_mix"].items()),
         "  - Quebec and Acadian surnames were added at 2.5%.",
         "  - Regional boosts for the southern Great Lakes heritages: Polish, Hungarian, Slavic, Arab, Dutch, Italian and German.",
         "  - The Asian share was split more fully to South Asian families.",
         "- **Twenty generations** of inheritance were simulated as a Galton-Watson branching process, with the population growing to the Balance and then holding.",
         "- **Result:** %d founding surnames, of which **%d are alive in 2752** and %d are extinct as surnames. The founder effect makes the commonest names more common." % (name_stats["founding_surnames"], name_stats["surnames_2752"], name_stats["extinct"]),
         "- **Top 40 in 2752:** " + ", ".join("%s (%d)" % (r[0], r[1]) for r in names["surnames"][:40]),
         "- **Heritage shares of surnames in 2752:** " + ", ".join("%s %.1f%%" % (k, v2 * 100) for k, v2 in names["surname_heritage_share_2752"].items()),
         "",
         "Surname heritage is the *name's* origin, not a person's ancestry: after 500 years everyone's ancestry is mixed. Many Black families carry English-derived surnames ('black_anglo'), as in the census.",
         "",
         "## Given names: pools and cohorts",
         "- **The pools:**",
         "  - `earth_old` (SSA 1880-1929), `earth_mid` (1930-1979) and `earth_new` (1980-2017), each the top 1,500 names by sex;",
         "  - the `heritage_*` pools (hand lists);",
         "  - `station` (the station's own coined names);",
         "  - `heroes` (the remembered people's first names);",
         "  - `vogue` (each present-era decade's fashions).",
         "- **Choosing a name:** the engine picks a pool by the birth cohort's mix, raising the heritage share for the family's heritage, then picks a name within the pool.", ""]
    L += md_table([(c["from"], c["to"], c["label"], ", ".join("%s %d%%" % (k, round(v2 * 100)) for k, v2 in c["mix"].items())) for c in names["cohorts"]], ["born from", "to", "cohort", "mix"])
    L += ["", "## The station's own names (by source)", ""]
    by = {}
    for s_ in ("F", "M"):
        for n_, wt, src in names["given_pools"]["station"][s_]:
            by.setdefault(src, set()).add(n_)
    L += ["- **%s:** %s" % (k, ", ".join(sorted(v2))) for k, v2 in by.items()]
    L += ["", "## Vogue names by decade", ""] + ["- **%s0s** F: %s; M: %s" % (d[:3], ", ".join(n for n, _ in v2["F"]), ", ".join(n for n, _ in v2["M"])) for d, v2 in names["vogue"].items()]
    L += ["", "## Heroes (named after the voyage's people)", "", "F: " + ", ".join(n for n, _ in names["given_pools"]["heroes"]["F"]), "", "M: " + ", ".join(n for n, _ in names["given_pools"]["heroes"]["M"])]
    L += ["", "## Heritage given names", ""] + ["- **%s** F: %s" % (h[9:], ", ".join(n for n, _ in names["given_pools"][h]["F"])) for h in names["given_pools"] if h.startswith("heritage_")]
    L += ["", "## Earth pools: the top 30 of each", ""] + ["- **%s %s:** %s" % (p, s_, ", ".join(n for n, _ in names["given_pools"][p][s_][:30])) for p in ("earth_old", "earth_mid", "earth_new") for s_ in ("F", "M")]
    L += ["", "## Nicknames", ""] + ["- %s: %s" % (k, ", ".join(v2)) for k, v2 in names["nicknames"].items()]
    L += ["", "## Notes", ""] + ["- **%s:** %s" % kv for kv in names["notes"].items()]
    w(os.path.join(D, "02_names.md"), L)

    # 03 history -----------------------------------------------------------------------------------------
    L = ["# 3. History", "", "Past: %d eras and %d events. The founding is kept as legend and ritual, the middle centuries as a thin outline, and VY 420-500 year by year." % (len(history["eras"]), len(history["events"])),
         "The `known` column says how the people of 2752 know each event, and `gist/detail` is the share of adults who know the gist and the details.", ""]
    for e in history["eras"]:
        L += ["## %s (VY %d-%d, %d-%d)" % (e["name"], e["vy"][0], e["vy"][1], e["ad"][0], e["ad"][1]), "", e["summary"], "",
              "- **Culture:** " + ", ".join("%s %.2f" % kv for kv in e["culture"].items()),
              "- **Governance:** %s. **Technology:** %s. **Memory now:** %s. **Key people:** %s" % (e["governance"], e["tech"], e["memory"], ", ".join(nm(p) for p in e["key_people"])), ""]
        rows = [(x["vy"], x["ad"], x["kind"], x["summary"], x["known"], "%d%%/%d%%" % (x["known_share"][0] * 100, x["known_share"][1] * 100), "; ".join(x["popular_version"]))
                for x in history["events"] if x["era"] == e["id"]]
        if rows:
            L += md_table(rows, ["VY", "AD", "kind", "what", "known", "gist/detail", "as people tell it"]) + [""]
    L += ["## The Moderators of the Assembly", "", "Names flagged * are generated from the name catalogue for the terms the canon doesn't name.", ""]
    L += md_table([("%d-%d" % tuple(m["term"]), m["name"] + ("" if not m["generated"] else " *"), m.get("home", "")) for m in history["moderators"]], ["term (VY)", "Moderator", "home"])
    L += ["", "## The Spin Cup (the Station League final), VY 201-499", "", "Years not fixed by the canon are generated from the teams' strength and era (flag *).", ""]
    rows, line = [], []
    for c in history["spin_cup"]:
        line.append("%d %s%s" % (c["vy"], c["team"].split()[-1], "*" if c["generated"] else ""))
        if len(line) == 10:
            rows.append(line)
            line = []
    if line:
        rows.append(line + [""] * (10 - len(line)))
    L += md_table(rows, [""] * 10)
    w(os.path.join(D, "03_history.md"), L)

    # 04 people ------------------------------------------------------------------------------------------
    L = ["# 4. People", "",
         "**Origins:**",
         "- *founder*: an Earth-born voyager, an immigrant aboard;",
         "- *station*: born aboard, a native;",
         "- *bank*: born aboard from the Ark Bank, a native;",
         "- *earth_side*: never aboard.",
         "",
         "`moved_to` marks people who migrated inside the station.",
         "Childless reasons use the share system's vocabulary: *gave_share* means they gifted their birth share to someone else's family.", ""]
    for era in ["earth_side", "founder", "station_dead", "living"]:
        title = {"earth_side": "Earth-side", "founder": "Founders (Earth-born voyagers)", "station_dead": "The station-born dead", "living": "The living (VY 500)"}[era]
        sel = [p for p in peo["people"] if (p["origin"] == era) or (era == "station_dead" and p["origin"] in ("station", "bank") and not p["alive"]) or (era == "living" and p["alive"] and p["origin"] != "earth_side")]
        if era == "founder":
            sel = [p for p in sel if not p["alive"]]
        L += ["## " + title, ""]
        L += md_table([("%s %s" % (p["given"], p["surname"]), p["sex"], "%s-%s" % (p["born_ad"], p["died_ad"] or ("missing" if p["missing"] else "")),
                        p["age_vy500"] if p["alive"] else "", p["title"], p["home"], p["origin"] + (" (moved)" if p["moved_to"] else ""),
                        "%s, %s" % (p["marital"], nm(p["spouse"]) if p["spouse"] in people else (p["spouse"] or "")), p["children"] if p["children"] else "0: " + str(p["childless"]),
                        p["faith"], p["reputation"], "%.2f" % p["fame"], "; ".join(p["notes"]))
                       for p in sorted(sel, key=lambda p: p["born_vy"])],
                       ["name", "sex", "born-died (AD)", "age", "title", "home", "origin", "marital", "children", "faith", "reputation", "fame", "notes"]) + [""]
    L += ["## Kin among them", ""] + ["- %s is %s %s" % (nm(k["a"]), k["rel"].replace("_", " "), nm(k["b"])) for k in peo["kin"]]
    w(os.path.join(D, "04_people.md"), L)

    # 05 lineages -------------------------------------------------------------------------------------
    L = ["# 5. Lineages (the great families)", "",
         "A lineage is a surname line and the lore that travels with it. The engine gives a person their lineage from their surname. The lineage then shades them:",
         "- trades;",
         "- faith;",
         "- temperament (small shifts on the Big Five means);",
         "- what the family is known for;",
         "- feuds and alliances (the affinity priors).",
         ""]
    for l in [x for x in lin["lineages"] if not x.get("minor")]:
        L += ["## %s (%s)" % (l["surname"], l["reputation"]),
              "- **Founder:** %s; **origin:** %s; **heritage:** %s; **bearers in 2752:** %d; **status:** %s" % (nm(l["founder"]) if l["founder"] else "(many founders)", l["origin"], l["heritage"], l["bearers_2752"], l["status"]),
              "- **Strongholds:** %s; **trades:** %s; **faith:** %s; **temperament tilt:** %s" % (", ".join(l["strongholds"]), ", ".join(l["trades"]), l["faith"], ", ".join("%s %+.2f" % kv for kv in l["tilt"].items()) or "none"),
              "- **Known for:** " + "; ".join(l["known_for"]),
              "- **Lore:** " + "; ".join(l["lore"]),
              "- **Members:** " + ", ".join(nm(m) for m in l["members"]),
              "- **Feuds:** " + ("; ".join("%s (%+.1f, %s)" % (f["with"], f["value"], f["why"]) for f in l["feuds"]) or "none") + "; **allies:** " + (", ".join(l["allies"]) or "none"), ""]
    L += ["## Minor lines (from the notable people)", ""] + md_table([(l["surname"], l["heritage"], ", ".join(l["strongholds"]), ", ".join(nm(m) for m in l["members"]), l["bearers_2752"]) for l in lin["lineages"] if l.get("minor")],
                                                                      ["surname", "heritage", "stronghold", "members", "bearers 2752"])
    w(os.path.join(D, "05_lineages.md"), L)

    # 06 culture ----------------------------------------------------------------------------------------
    L = ["# 6. Culture in VY 500", "", "The founders' Great Lakes ways and what 500 years aboard made of them. `origin` shows where each came from; *station* means it was invented aboard.", "", "## Holidays"]
    L += md_table([(h["name"], h["date"], h["origin"], h["since_vy"], "%d%%" % (h["share"] * 100), "; ".join(h["activities"]), ", ".join(h["foods"]), h["notes"]) for h in cul["holidays"]],
                  ["holiday", "date", "origin", "since VY", "observe", "what", "food", "notes"])
    L += ["", "## Foods"] + md_table([(f["name"], f["kind"], f["origin"], f["when"], ", ".join(f["places"]), f["notes"]) for f in cul["foods"]], ["food", "kind", "origin", "when", "where", "notes"])
    L += ["", "## Life-cycle rites"] + md_table([(r["name"], r["stage"], r["what"], r["origin"]) for r in cul["rites"]], ["rite", "when", "what", "origin"])
    L += ["", "## Everyday customs"] + ["- **%s:** %s" % (c["name"], c["what"]) for c in cul["customs"]]
    L += ["", "## Lexicon (Columbian English)"] + md_table([(l["term"], l["meaning"], l["origin"], l["who"], l["example"]) for l in cul["lexicon"]], ["term", "meaning", "origin", "who says it", "example"])
    L += ["", "## Sayings"] + ["- %s (%s)" % (s_["saying"], s_["use"]) for s_ in cul["sayings"]]
    L += ["", "## Beliefs about the voyage, the Steward and Earth"] + md_table([(b["belief"], "%d%%" % (b["share"] * 100), b["source"], b["held_by"]) for b in cul["beliefs"]], ["belief", "adults holding it", "source", "held by"])
    L += ["", "## Superstitions"] + ["- " + s_["what"] for s_ in cul["superstitions"]]
    L += ["", "## Etiquette"] + ["- " + s_["what"] for s_ in cul["etiquette"]]
    L += ["", "## Taboos"] + ["- %s (strength %.1f)" % (t["what"], t["strength"]) for t in cul["taboos"]]
    L += ["", "## Pastimes"] + md_table([(p["name"], p["kind"], p["what"], "%d%%" % (p["share"] * 100)) for p in cul["pastimes"]], ["pastime", "kind", "what", "share"])
    L += ["", "## Arts and media"] + ["- **%s** (%s): %s" % (a["name"], a["kind"], a["what"]) for a in cul["arts"]]
    d = cul["dialect"]
    L += ["", "## Dialect", "", d["base"], ""] + ["- **%s:** %s" % (k, "; ".join(v2)) for k, v2 in d.items() if k != "base"]
    L += ["", "## What changed from Earth"] + md_table([(c["origin"], c["now"], c["why"]) for c in cul["changes"]], ["Great Lakes origin", "on Columbia", "why"])
    L += ["", "## Schooling", ""] + ["- **%s:** %s" % (k, v2 if isinstance(v2, str) else "; ".join(v2)) for k, v2 in cul["schooling"].items()]
    w(os.path.join(D, "06_culture.md"), L)

    # 07 settlements ----------------------------------------------------------------------------------
    L = ["# 7. Settlements at full scale (250,000 people)", "", "`test_town` is the town's name in the engine's condensed test map, which holds a small sample of its population.", ""]
    for s_ in settlements:
        L += ["## %s (%s, %s people, founded VY %d%s)" % (s_["name"], s_["kind"], "{:,}".format(s_["pop"]), s_["founded_vy"], ", a Charter Town" if s_["charter_town"] else ""),
              "- **Region:** %s; **engine archetype:** %s; **named for:** %s" % (s_["region"], s_["archetype"], nm(s_["named_for"]) if s_["named_for"] in people else s_["named_for"]),
              "- **Character:** " + "; ".join(s_["character"]),
              "- **Economy:** " + "; ".join(s_["economy"]),
              "- **Districts:** " + ("; ".join(s_["districts"]) or "-"),
              "- **Heritage lean:** %s; **faith lean:** %s" % (", ".join("%s x%.1f" % kv for kv in s_["heritage_lean"].items()) or "average", ", ".join("%s x%.1f" % kv for kv in s_["faith_lean"].items()) or "average"),
              "- **Landmarks:** " + "; ".join(s_["landmarks"]),
              "- **Rivals:** %s; **allies:** %s; **reputation:** %s" % (", ".join(s_["rivals"]) or "none", ", ".join(s_["allies"]) or "none", ", ".join(s_["reputation"])), ""]
    w(os.path.join(D, "07_settlements.md"), L)

    # 08 outside world -------------------------------------------------------------------------------------
    L = ["# 8. The outside world, and the future", "", "## Earth, the Earth-link and the other arks", ""]
    L += md_table([(x["ad"], x["kind"], x["summary"], "; ".join(x["detail"]), x["known"], "; ".join(x["popular_version"])) for x in history["events"] if x["scope"] == "earth"],
                  ["AD", "kind", "what", "detail", "known now", "as people tell it"])
    L += ["", "## The future (known to no one aboard)", "", "This section is sparse by design. The engine may foreshadow it but never state it.", ""]
    L += md_table([(e["name"], "VY %d-%d" % tuple(e["vy"]), "%d-%d" % tuple(e["ad"]), e["summary"]) for e in history["future_eras"]], ["era", "VY", "AD", "what"])
    L += [""] + md_table([(e["vy"], e["ad"], e["kind"], e["summary"], e["hook_for_present"]) for e in history["future_events"]], ["VY", "AD", "kind", "what", "hook in the present"])
    w(os.path.join(D, "08_outside_world.md"), L)

    # 09 affinity --------------------------------------------------------------------------------------------
    L = ["# 9. Affinity: how people feel about each other and about the player", "",
         "The user asked (2026-09-30) for **affinity to be tracked toward the player and between characters**. The player builds their own mythos through the people they meet.",
         "This page covers the priors the bible supplies, how they combine, and what's stored. The psychology framework (`research/psychology/06`) owns the opinion tokens; these are their starting points.", "",
         "## 1. The prior between two characters, A(i to j) in [-1, 1]",
         "Every term is computed from generated or stored facts, so nothing needs storing until someone does something:",
         "- **kin:** same household +0.45; parent or child +0.5; sibling +0.4; grandparent +0.35; cousin +0.15; share-kin (a child of my gifted share) +0.3;",
         "- **lineage:** same lineage +0.08; the lineages' feud value (for example Moriarty and Castellanos -0.6); alliance +0.2 (lineages.json);",
         "- **factions:** the faction affinity table below, x 0.5 per pair of memberships (factions.json);",
         "- **settlement:** same town +0.05; rival towns -0.3; allied towns +0.2; plus the region term (North Shore v. South Shore -0.15);",
         "- **faith:** same faith +0.1 (x 1.5 when both attend weekly); the faith affinity table;",
         "- **familiarity:** same workplace +0.15; same regular place +0.05 per shared place (NpcLife anchors); neighbours +0.05;",
         "- **temperament:** + 0.2 x (i's agreeableness - 0.5); - 0.1 when i is high in neuroticism and j is a stranger;",
         "- **reputation:** + 0.1 x j's reputation valence if i knows of j (fame, and the knowledge the propagation engine delivers).", "",
         "## 2. Toward the player",
         "The player starts as a **stranger from somewhere else aboard**. The user chooses the home town, and the AI adapts.",
         "- The prior is the settlement term for the player's chosen town against each character's, plus the region term. A Port Carrow player in Solana Point starts at about -0.3 with keen Suns fans.",
         "- The first impression comes from dress, manner and the first line, via the psychology framework's appraisal.",
         "- After that, only events move it: deeds witnessed or heard of through propagation, gifts, promises, insults.", "",
         "## 3. What's stored",
         "- **Sparse deltas only:** (i, j) maps to a list of {delta, cause (event token), day, decay}. The prior is always recomputed.",
         "- **Decay:** small kindnesses and slights fade (half-life about 60 days); betrayals, rescues and deaths don't.",
         "- **Scope:** deltas are stored for anyone the player has touched directly, or at one to three hops through propagation.",
         "- **Between characters:** deltas are stored only when an event involves both, such as a feud started by the player's meddling. Everyone else runs on priors.",
         "- **Size:** tens of bytes per pair touched. A long game touches a few thousand pairs.", "",
         "## 4. The player's mythos",
         "The player's own history is the story engine's chronicle (story 04 §2.9): a list of arcs, each with roles, beats and mythos.",
         "Affinity is the quantitative side of that chronicle. Together they are the player's standing in each town, family and faction, and the NPCs quote it back.", "",
         "## Faction affinity (priors)"]
    L += md_table([(x["a"], x["b"], "%+.2f" % x["value"]) for x in fac["faction_affinity"]], ["faction", "faction", "value"])
    L += ["", "## Factions", ""] + ["- **%s** (%s, about %.1f%% of adults%s): %s; strong in %s; leaders %s" % (f["name"], f["kind"], f["share"] * 100, ", secret" if f.get("secret") else "", "; ".join(f["holds"]),
                                                                                                                   ", ".join(f["strong_in"]), ", ".join(nm(p) for p in f["leaders"]) or "-") for f in fac["factions"]]
    L += ["", "## Faith affinity", ""] + ["- %s / %s: %+.2f" % (x["a"], x["b"], x["value"]) for x in fac["faith_affinity"]]
    L += ["", "## Regions", ""] + ["- %s / %s: %+.2f" % (x["a"], x["b"], x["value"]) for x in fac["region_affinity"]]
    w(os.path.join(D, "09_affinity.md"), L)

    # 10 engine ------------------------------------------------------------------------------------------------
    L = ["# 10. How the engine uses the bible", "",
         "| file | used for |", "|---|---|",
         "| names.json | NpcNames: a household's surname (weighted by the town's heritage leans and the lineage strongholds) and each member's given name (sex, birth year's cohort mix, family heritage), plus nicknames |",
         "| lineages.json | a surname's lineage gives trade and faith tendencies, temperament tilts, lore lines for dialogue, and feud and alliance priors |",
         "| settlements.json | full-scale town facts: archetype, heritage and faith leanings, rivals, reputation (dialogue: 'Pointers are loud') |",
         "| history.json | what a person knows (the knowledge level x their age, schooling, faith and family), and the popular versions to quote; living memory by birth year; the Moderators and Spin Cups for small talk |",
         "| people.json | living notables pinned into the world (home, occupation, age, sex, family); the dead as memory and reputation; descendants through lineages |",
         "| factions.json | membership by the `draws` rules; affinity priors (09) |",
         "| culture.json | holidays drive NpcLife (closures, parades, church); foods drive places' stock; lexicon and sayings go to the dialogue prompt; beliefs weight what a person thinks of the Notice |",
         "| world.json | the frame of every prompt: the date (VY 500), the Steward, the calendar, the land |",
         "", "## Counts", ""] + ["- %s: %s" % kv for kv in counts.items()]
    L += ["", "## Rebuild", "", "`python3 tools/bible/make_bible.py`: names, canon, checks, JSON and these pages, in about 15 s. It fails on any broken reference."]
    w(os.path.join(D, "10_engine.md"), L)


def write_industry(D, ind, peo, history):
    people = {p["id"]: p for p in peo["people"]}
    nm = lambda pid: "%s %s" % (people[pid]["given"], people[pid]["surname"]) if pid in people else pid
    evs = {e["id"]: e for e in history["events"]}
    sw = ind["steward_works"]
    L = ["# 12. Industry: the Steward's works, the boards and the vehicle works", "",
         "Canon from the user (2026-10-01), detailed here. Engineering numbers for the boards are in `tools/vehicles/platforms.py`",
         "(`godot_project/remake/vehicles/chassis/platforms.json`); the chassis models are built from them (`remake/blender/chassis/chassis.py`).", "",
         "## The Rock", ""]
    for k in ("what", "size", "mining"):
        L.append("- **%s:** %s" % (k, sw["the_rock"][k]))
    L += ["- **role:** " + "; ".join(sw["the_rock"]["role"]), "", "## The Spindle", ""]
    for k in ("what", "fed_by", "people"):
        L.append("- **%s:** %s" % (k, sw["the_spindle"][k]))
    L += ["- **inside:** " + "; ".join(sw["the_spindle"]["inside"]), "", "## What the Steward makes for people", ""]
    L += md_table([(a, b, c) for a, b, c in sw["makes_for_people"]], ["id", "what", "how often"])
    d = ind["drops"]
    L += ["", "## The Drops", "", d["what"] + ".", "", "_" + d["_about"] + "_", ""] + ["- **%s:** %s" % kv for kv in d["kinds"]]
    L += ["", "- **versus the Chutes:** " + d["versus_chutes"], "- **words:** " + "; ".join(d["words"]), "", "## The limits the Steward keeps", ""]
    t = ind["tech_limits"]
    L += ["### %s" % t["processors"]["name"], "", t["processors"]["what"] + ".", "",
          "- **supply:** " + t["processors"]["supply"], "- **used in:** " + "; ".join(t["processors"]["use"]),
          "- **know-how:** " + t["processors"]["know_how"], "- **the cap:** " + t["processors"]["the_cap"], "",
          "### Panels", "", t["panels"]["what"] + ".", "", "- **priority:** " + " > ".join(t["panels"]["priority"]), "- **vehicles:** " + t["panels"]["vehicles"], "",
          "### Gauges", "", t["gauges"]["what"] + "; made by " + t["gauges"]["makers"] + ".", "",
          "### The Wire slot", "", t["radio"]["what"] + ".", "",
          "- **slot:** %(w_mm)d x %(h_mm)d mm, %(depth_mm)d mm deep; %(connector)s" % t["radio"]["slot"], "- **origin:** " + t["radio"]["origin"], "- **culture:** " + t["radio"]["culture"], "",
          "**Why:** " + t["why"], "", "## The boards", "", "**%s:** %s %s" % (ind["platforms"]["pattern"]["name"], ind["platforms"]["pattern"]["what"], ind["platforms"]["pattern"]["law"]) + ".", ""]
    for b in ind["platforms"]["boards"]:
        L += ["### %s" % b["name"], "", "- **maker:** %s, since VY %d%s" % (b["maker"], b["since_vy"], " (never changed)" if b["unchanged"] else ""),
              "- **called:** " + ", ".join(b["folk"]), "- **build:** " + b["build"], "- **look:** " + b["look"], "- **sizes:** " + ", ".join(b["sizes"]),
              "- **used for:** " + ", ".join(b["used_for"]), ""]
    L += ["## How things are made", "", "### The Steward", ""] + ["- **%s:** %s" % kv for kv in ind["manufacturing"]["steward"]]
    L += ["", "### People", ""] + ["- **%s:** %s" % kv for kv in ind["manufacturing"]["people"]]
    L += ["", "## The vehicle works", ""]
    for c in ind["companies"]:
        L += ["### %s (%s)" % (c["name"], c["short"]), "",
              "- **seat:** %s; %s" % (c["seat"], c["yard"]), "- **founded:** VY %d by %s" % (c["founded_vy"], ", ".join(nm(p) for p in c["founders"])),
              "- **board:** %s" % c["board"], "- **ethos:** " + c["ethos"], "- **colours:** " + ", ".join(c["colours"]),
              "- **buyers:** " + c["buyers"], "- **strong in:** " + ", ".join(c["strong_in"]), "- **Steward allotment:** " + c["allotment"],
              "- **reputation:** " + c["reputation"], "- **now (VY 500):** " + c["now"], "", "**People:**", ""]
        for pid in c["people"]:
            p = people[pid]
            life = "b. VY %d" % p["born_vy"] if p["alive"] else "VY %d-%s" % (p["born_vy"], p["died_vy"])
            L.append("- **%s** (%s): %s. %s" % (nm(pid), life, p["title"], " ".join(p["notes"])))
        L += ["", "**History:**", ""]
        for eid in sorted(c["events"], key=lambda e: evs[e]["vy"]):
            e = evs[eid]
            L.append("- VY %d%s: %s" % (e["vy"], "-%d" % e["end_vy"] if e.get("end_vy") else "", e["summary"]))
        L.append("")
    L += ["## Rivalries", ""] + ["- %s / %s (%+.1f): %s" % (r["a"], r["b"], r["value"], r["why"]) for r in ind["rivalries"]]
    w(os.path.join(D, "12_industry.md"), L)
