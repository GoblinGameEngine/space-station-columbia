"""Columbia game bible: the outside world. Earth before the launch (broad strokes: why an ark, why
the southern Great Lakes, why a continent's people), the Earth-link after it (what came over the
wire, and when it stopped making sense), the other arks, and the destination.

Every entry is an event record (see make_bible.py EVENT_FIELDS). 'known' is how the people of
2752 know it (WORLD.knowledge_levels); 'known_share' is [gist, detail] among adults.
Pre-launch Earth history is the bible's fiction extrapolated from real trends to 2025; it is
deliberately broad and names no present-day governments' policies.
"""

def E(id, ad, kind, summary, detail=(), end=None, where=("earth",), people=(), effects=(), known="legend", share=(0.3, 0.02),
      popular=(), stories=(), tags=()):
    return dict(id=id, ad=ad, end=end, kind=kind, where=list(where), people=list(people), summary=summary, detail=list(detail),
                effects=list(effects), known=known, known_share=list(share), popular_version=list(popular), story_types=list(stories),
                tags=list(tags), era="prelude_earth" if ad < 2252 else None)


EARTH_EVENTS = [
    E("earth_hot_century", 2030, "disaster", "the Hot Century: heat, drought, storms and rising seas reshape where people can live",
      ["the American South and Southwest, the Gulf and Atlantic coasts and much of Mexico and the Caribbean become hard to live in",
       "fresh water becomes the continent's measure of wealth"], end=2130,
      effects=["migration:toward_great_lakes"], known="legend", share=(0.55, 0.03),
      popular=["'Earth got too hot'", "'the old world burned'", "a Sunday-school story of a flood of fire"], stories=["community_crisis"], tags=["why_we_left"]),
    E("great_lakes_refuge", 2060, "migration", "the Refuge: tens of millions move to the Great Lakes basin, the continent's cool, water-rich heart",
      ["from Texas, Florida, Arizona, Louisiana, the Carolinas, Georgia, California, from Mexico, Puerto Rico, Cuba, Haiti, the Dominican Republic and Central America, and from Canada's burning west",
       "Toledo, Cleveland, Detroit, Chicago, Buffalo, Milwaukee, Erie and Windsor double and double again",
       "the southern Great Lakes become the most diverse region on the continent; the old Great Lakes ways (the fish fry, euchre, the parish festival, polka and the Friday night game) become everyone's"],
      end=2160, effects=["founders:continental_diversity", "culture:great_lakes_core"], known="ritual", share=(0.35, 0.05),
      popular=["'we came from the Lakes'", "'everyone came to the Lakes, then the Lakes came here'"], stories=["stranger_arrives", "found_family"], tags=["why_great_lakes"]),
    E("lakes_megaregion", 2110, "economy", "the Lakes megaregion: the continent's industrial and scientific centre (fusion, space industry)",
      ["fusion power stations along the lake shores", "shipyards turn to spacecraft; Cleveland, Toledo and Detroit build for the Moon"],
      end=2200, known="scholar", share=(0.03, 0.005), tags=["industry"]),
    E("lunar_industry", 2140, "science", "lunar mining and orbital yards make large ships possible", ["the L2 yards", "asteroid ice and metals"],
      known="scholar", share=(0.02, 0.005)),
    E("hesperus_array", 2181, "discovery", "the Hesperus interferometer finds oxygen on a planet of Alpha Centauri A: Hesper",
      ["0.92 Earth masses, 1.23 AU, oceans", "the find electrifies the continent"], known="legend", share=(0.2, 0.01),
      popular=["'the green star'", "'the Far Shore'", "some think Hesper is Heaven"], stories=["wonder", "quest"], tags=["destination"]),
    E("compact_founded", 2198, "political", "the North American Interstellar Compact founded at Toledo to build an ark for Hesper",
      ["the US, Canada and Mexico, the Great Lakes states and provinces, companies and churches", "Dr. Ingrid Kessler its first director-general",
       "motive: 'a second home for the continent' (the Second Home movement), insurance against the Hot Century's return, and the pull of Hesper"],
      people=["ingrid_kessler"], known="schooled", share=(0.25, 0.04), popular=["'the Compact'", "'Kessler built the ship'"], stories=["daring_enterprise"], tags=["founding"]),
    E("columbia_design", 2206, "science", "the Columbia design fixed: one cylinder, seas at the ends, a Sunline, and towns patterned on the Great Lakes' own",
      ["the Heritage Mandate: towns built to the plans of real historic buildings from the Library of Congress archive (the pattern buildings), so the voyagers would live in familiar streets",
       "European engineers (the ESA drive team under Henrik Aaltonen) design the drive and the rotation bearings"],
      people=["henrik_aaltonen", "ingrid_kessler"], known="scholar", share=(0.04, 0.01),
      popular=["people think the old buildings were 'brought from Earth'"], tags=["heritage_mandate"]),
    E("yard_construction", 2214, "construction", "construction at the L2 yard", ["37 years; 11,000 builders; 212 deaths in yard accidents"], end=2251,
      known="scholar", share=(0.05, 0.005), popular=["'it took a hundred years to build'"], tags=["founding"]),
    E("steward_commissioned", 2238, "science", "the Habitat Autonomy System (the Steward) commissioned to run the ship for three thousand years",
      ["designed so that the voyagers need never understand the machinery", "a three-thousand-year service life written into its core (the Long Clause)"],
      people=["amara_nwosu"], known="scholar", share=(0.03, 0.002), popular=["'the Steward was always here'", "'God made the Steward'", "'the founders built a mind'"],
      stories=["enigma"], tags=["steward", "future_hook"]),
    E("the_selection", 2240, "migration", "the Selection: 72,000 voyagers chosen from 4.1 million applicants in the Lakes megaregion",
      ["half by lottery, half by trade (the Trades list: farmers, fishers, builders, teachers, nurses, doctors, engineers, cooks, musicians, clergy)",
       "families went together; the genetic survey ensured diversity; a frozen bank of 1.2 million embryos and gametes (the Ark Bank) went too"],
      end=2250, known="ritual", share=(0.4, 0.03), popular=["'our ancestors won a lottery'", "'only the best were chosen'", "'Grandmother X was a cook on the Trades list'"],
      stories=["daring_enterprise", "hard_choice"], tags=["founders"]),
    E("the_goodbyes", 2251, "migration", "the Goodbyes: the voyagers leave their homes and families; ferried up to the yard over eight months",
      ["most left parents, siblings and friends behind forever", "the last ferry left Toledo Port on 30 March 2252"], known="ritual", share=(0.45, 0.03),
      popular=["'Goodbye Day' songs", "the custom of leaving an empty chair at Launch Day dinner"], stories=["grief", "abandonment", "earthsick"], tags=["founders"]),
    # the Earth-link after launch
    E("link_early_letters", 2252, "contact", "the Letters: families on Earth write to the voyagers; replies take weeks, then months", [], end=2340,
      where=("earth", "station"), known="family", share=(0.2, 0.02), popular=["families keep 'Earth letters' in tins"], stories=["letters"], tags=["earth_link"]),
    E("link_last_relatives", 2320, "contact", "the last people on Earth who knew a voyager die; the Letters become official news bulletins", [],
      where=("earth", "station"), known="scholar", share=(0.02, 0.002), tags=["earth_link"]),
    E("link_green_message", 2483, "contact", "the Green Message: Earth reports the Hot Century's damage healed and invites the ark to consider return (a proposal, never an order)",
      ["the trigger of the Returners movement and the Troubles"], where=("earth", "station"), known="legend", share=(0.35, 0.04),
      popular=["'Earth called us home'", "'Earth lied to tempt us back'", "'there was no message; the Returners made it up'"], stories=["temptation", "divided_loyalty"], tags=["earth_link", "troubles"]),
    E("link_last_letter", 2643, "contact", "the Last Letter: Earth's last message in plain language, strange in tone and hard to understand",
      ["afterward only an automated pulse (the Heartbeat) every 29 days", "Bellhaven scholars still argue what the Last Letter means"],
      where=("earth", "station"), known="scholar", share=(0.08, 0.01), popular=["'Earth went quiet'", "'Earth forgot us'", "'Earth became angels' (Waymaker lore)"],
      stories=["enigma", "letters", "abandonment"], tags=["earth_link", "mystery"]),
    E("link_heartbeat", 2643, "contact", "the Heartbeat: an automated pulse from Earth every 29 days; the Steward logs it; nobody reads it", [], end=None,
      where=("earth", "station"), known="scholar", share=(0.05, 0.005), popular=["'the Heartbeat means Earth is still there'"], stories=["enigma"], tags=["earth_link"]),
    # other arks (known through the Letters)
    E("ark_harmonia", 2238, "migration", "the ark Harmonia (European Union) launched for Tau Ceti", ["contact lost 2279 (VY 27)"],
      known="legend", share=(0.1, 0.01), popular=["'Harmonia was lost'", "sailors' ghost stories of a ship 'following ours'"], stories=["enigma"], tags=["other_arks"]),
    E("ark_tianhe", 2244, "migration", "the ark Tianhe (China) launched for Epsilon Eridani", ["reported healthy in the Last Letter era"],
      known="scholar", share=(0.03, 0.005), tags=["other_arks"]),
    E("ark_kaveri", 2261, "migration", "the ark Kaveri (India and the Gulf states) launched for Alpha Centauri B", ["will arrive after Columbia; the Letters mention it until 2410"],
      where=("earth",), known="scholar", share=(0.02, 0.005), popular=["'the ship behind us' (a Waymaker belief: the Kaveri follows Columbia)"], stories=["enigma"], tags=["other_arks", "future_hook"]),
    E("ark_pampa", 2290, "migration", "the ark Pampa (the South American League) launched for 82 Eridani", [],
      known="lost", share=(0.0, 0.0), tags=["other_arks"]),
]
