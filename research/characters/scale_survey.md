# Characters at scale: how other games and simulations do it, and the theory behind it

Our target is worlds with **hundreds of thousands of characters**. Each one should be
individually generated (body, face, clothing, and later personality, ties and a place in the
story), appear on demand, and be the same person every time, with nothing stored unless the
player changes them. This file surveys everything we could find that works at comparable scale
and pulls out the methods and the theory. Local copies of the papers are in `reference/papers/`.

---

## 1. Systems at comparable scale

| system | population | explicit (individually tracked) | abstract / regenerated | promotion trigger | appearance |
|---|---|---|---|---|---|
| **Watch Dogs: Legion** (Ubisoft Toronto 2020), Census | "nearly 9 million" characters | uprezzed NPCs: "hundreds" live, cycled out when stale | background NPCs are generated, then **deleted** when the player moves away | scanned with the profiler, interacted with, cast in a mission, or **connected** to an uprezzed person | outfit and style by income and occupation; voices recorded 20+ times per line, then formant-shifted |
| **Ultima Ratio Regum** (Johnson), roguelike | ~**10 million** NPCs per world; "over 1 trillion possible" | 500–700 "important" NPCs always simulated, chosen by an importance measure | everyone else "abstracted out" | the importance measure rises (and falls back) | faces from per-genetic-group feature sets; clothing by culture |
| **Dwarf Fortress** (Adams), world generation | hundreds of thousands of **historical figures** over millennia, plus abstract populations | histfigs: full history, relationships, kills, titles | site populations are **numbers**; unnamed people are created on the spot and vanish when you leave | citizenship, birth to a histfig mother, being named, killing, bonding, meeting an adventurer | appearance modifiers per body part, 7 descriptor bands, genetically inherited |
| **Cities: Skylines** (Colossal Order 2015) | ~1M citizens | 65,536 agent instances moving about | the rest are records: home, work, age, education, grouped into "citizen units" | a trip needs to happen | a few models per age and sex |
| **Cities: Skylines II** (2023) | no fixed cap | ECS-simulated households and citizens | – | – | – |
| **Assassin's Creed Unity** (Ubisoft Montreal 2014) | crowds up to ~30,000; 10,000 on screen | **40** real AIs and **120** high-resolution models | "bulk" crowd: 11 bones, a tenth of the polygons, 29 variants | nearness to the player: pooled swap from low to high resolution, unnoticed ("AI recycling", GDC 2015) | close range uses the full character generator |
| **Hitman: Absolution** (IO 2012) | 1,200-person crowds at 30 fps | – | cell-based crowd simulation | – | – |
| **Crusader Kings III** | tens of thousands of living characters | all simulated | none; performance is managed by **pruning** and fewer spawns | – | DNA genes (see `character_creators.md`) |
| **Shadow of Mordor** (Monolith 2014), Nemesis | dozens of named orcs from an anonymous horde | captains with rank, traits and memory of the player | grunts | **killing the player** promotes the killer: name, title, voice lines | procedural combinations of parts |
| **Talk of the Town** (Ryan et al.) | 300–500 townspeople over 140 years | all, with beliefs about each other | – | – | 24 heritable facial attributes |
| **SPEW / synthetic populations** (epidemiology, transport) | **5+ billion** agents, 70+ countries | every agent is a record | – | – | none: demographic attributes only |

What all of these show: **nobody simulates everyone.** Every large system splits the population
into a small explicit set and a large abstract one, and **promotes** people when they become
relevant. The differences lie in what the abstract layer is (a number, a record, nothing at all)
and in what happens to someone who drops back out of relevance.

---

## 2. The methods, one by one

### 2.1 Tiers and promotion (level of detail for people)
- **Watch Dogs: Legion** has three layers: on screen; "uprezzed" (in the player's database, full
  profile, schedule simulated, even the path between places, so the player can intercept); and
  background. The uprezzing is a **spider web**: "we start with one fact about a person and then
  … add more facts … until at the very end of the uprez process, what you now have is a
  completely unique character" (Liz England). Generation can start from **whichever fact is
  already fixed**: the person seen in a bar fight has their personality fixed first, and their
  occupation is generated to fit.
- **Connections promote too:** the family and friends of an uprezzed character are uprezzed
  with them, so the web around anyone the player knows is consistent.
- **Ultima Ratio Regum:** an explicit importance measure, 500–700 at a time, and demotion when
  it drops.
- **Assassin's Creed Unity:** a pool of full NPCs is re-dressed as the player approaches
  bulk-crowd members ("recycling").
- **Dwarf Fortress:** a promotion list (named, killed someone, met the adventurer). A histfig
  is permanent.
- Academic basis: AI level of detail (Brom et al.), alibi generation (Sunshine-Hill & Badler
  2010), both in `procedural_npcs.md`.

**For us:** layers L0–L3 (`procedural_npcs.md`) are the same idea. Legion adds two refinements:
**connection promotion** (touch one person and their household and ties become fixed), and
**any-fact-first generation** (the request can pin any trait, and the rest is generated
consistent with it). We do this with pinned traits: a pinned value short-circuits its stream,
and the dependent traits still derive from it.

### 2.2 The abstract layer
There are three ways a population can exist without being tracked:
1. **As a number** (Dwarf Fortress sites, Victoria-style population groups): cheap, but a
   person drawn from it has no past.
2. **As a record** (Cities: Skylines citizens, epidemiological synthetic populations): tens of
   bytes each; a million is megabytes.
3. **As a function** (Watch Dogs' background layer, Elite's galaxy, No Man's Sky): nothing is
   stored; the person is recomputed from a seed.

Legion's background NPCs are generated then **discarded**: the same passer-by is not there
tomorrow unless uprezzed. We want more than that: **every resident has a permanent identity** (an
address: building and member index) and regenerates identically. That is option 3 with stable
addresses. It costs nothing to store, and it means a player can follow anyone home, come back a
week later and find them again. No surveyed game does this for its whole population.

### 2.3 Deterministic randomness
- **Noise-based RNG** (Eiserloh, "Math for Game Programmers: Noise-Based RNG", GDC 2017): replace
  stateful RNGs with a hash of (seed, position/index). This gives random access, order
  independence, lock-free parallelism, and trivial record and replay. Our per-trait streams
  (`hash(seed | person | trait)` → splitmix64) are this principle: any trait of any person is
  computable directly, in any order, on any thread.
- **Elite** (1984) fitted 8 galaxies of 256 systems into kilobytes the same way: the world is a
  function of a seed.

### 2.4 Populations that match real statistics
**Population synthesis** is the transport and epidemiology literature's answer to "make
millions of people consistent with census tables":
- **IPF** (iterative proportional fitting; Deming & Stephan 1940; applied to synthetic
  populations by Beckman et al. 1996) estimates the joint distribution from known marginals,
  then samples households, not individuals.
- **SPEW** (Gallagher et al. 2017) did this for 5 billion agents with workplaces and schools.
- The key idea for us: **sample households, then people inside them.** Individual sampling
  gets the ages right but not the families: no three-generation farm households, no student
  flats, no couples whose ages match.

**For us:** L0 should be household-first. For each residential building, a household type is
drawn from the town archetype (single, couple, family with children, three generations, shared
student house, retired couple), then the members are drawn consistent with it (ages, relations,
who works). Our `populations` in `npc_traits.json` give per-archetype marginals; the household
table is the next piece.

### 2.5 Appearance variety that people actually perceive
- **"Clone Attack! Perception of Crowd Variety"** (McDonnell, Larkin, Dobbyn, Collins &
  O'Sullivan, SIGGRAPH 2008):
  - appearance clones are far easier to spot than motion clones;
  - colour variation, random orientation and motion mask appearance clones.
- **"Eye-catching Crowds: Saliency based selective variation"** (McDonnell et al., SIGGRAPH 2009),
  with eye tracking:
  - the **head and upper torso** get most first fixations, whatever the character's
    orientation, sex, age, size or clothing;
  - selective colour variation is as effective as full variation;
  - **head accessories, top texture and face texture** variation are all equally effective, while
    **facial geometry alterations are less so**.
- **Thalmann, Maïm, Yersin (EPFL):** a few templates plus colour segmentation maps,
  accessories and skeleton scaling give each crowd member uniqueness.
- **Kate Compton's "10,000 bowls of oatmeal":** mathematically unique ≠ perceptually different.

**For us:** spend the variation budget where the eye goes:
1. hair silhouette and colour;
2. hats and head accessories;
3. the top garment's colour and pattern;
4. face colouring (brows, blush, freckles, glasses);
5. body silhouette (height, build);
6. and only then fine facial geometry.

This matches the Ghibli design rules (`ghibli_style.md` §1.2), where individuality is in hair,
face and accessories. With a few hundred thousand people the problem is not uniqueness (the
trait space is astronomically large) but **perceptual distinctness among the people on screen
at once, and memorability of the people the player meets.** The spawner's twin check
(`procedural_npcs.md` §3) should compare these salient features, not the full trait vector.

### 2.6 Generating bodies and faces that never fail
The user's requirement: generate bodies and faces "reliably without fail". The literature and
production practice agree on how:
1. **Bounded, data-constrained spaces.** Morphable models (Blanz & Vetter 1999) and body models
   (SMPL, Allen et al. 2006) represent shapes as combinations of real examples, and plausible
   shapes lie near the data. MetaHuman blends "between actual examples in the library in a
   plausible, data-constrained way". Bannerlord bounds every face by min and max templates per
   culture. Dwarf Fortress bounds every feature to 7 descriptor bands.
2. **Convex combinations of valid exemplars.** If every sculpted extreme is valid and they share
   topology and rig, blends with non-negative weights summing to at most 1 stay valid in
   practice. This is why the body triangle (Fallout 4, Starfield) is robust: it can't leave the
   triangle.
3. **Correlated sampling:** body measurements are correlated (height with leg length,
   weight with girth). Allen 2006 and the CAESAR/ANSUR anthropometric data show that sampling
   each independently produces implausible people. We should sample a few latent factors (age,
   sex, build triangle, height) and derive the rest.
4. **Construction guarantees:** one skeleton, one base topology, and garments authored on the
   same shape keys. Every parameter is clamped. The generator is **total**: every seed maps to a
   valid person, with no rejection loops that could fail to terminate.
5. **Corner testing:** test the extremes of every parameter together (the corners of the
   parameter box). If the corners are clean and the space is built from convex blends, the
   interior is clean. Plus bulk statistical tests, like Legion's 100-lawyer review and our
   `traits.py --stats`.
6. **Morphology-independent animation:** Spore (Hecker et al., SIGGRAPH 2008) authored
   animation in a generalised space and specialised it per creature with IK. Our morphologies
   vary far less (one humanoid skeleton), so standard retargeting plus foot and hand IK covers it,
   but the principle holds: animation must not assume one body.

### 2.7 Culture, speech and names as generated systems (for the next phases)
- **Ultima Ratio Regum** generates cultures, religions (over a million possible) and dialects:
  per-nation syllable sets, "references" from geography and beliefs, name archetypes, greetings
  and insults, and sentence complexity (Johnson, DiGRA-FDG 2016; AISB 2015). NPC behaviour is
  driven by cultural affiliation ("qualitative AI").
- **Caves of Qud** (Grinblat, GDC 2018) generates historical events first and **rationalises**
  them after the fact, instead of simulating history. This is the same move as alibi generation,
  applied to backstory.
- **James Ryan, *Curating Simulated Storyworlds*** (PhD, UC Santa Cruz 2018): simulation
  overgenerates and **curation / story sifting** finds the stories; Talk of the Town, Hennepin,
  Bad News.

These belong to the psychological and interpersonal phase. They are noted here because they
shape what the character record must be able to hold.

---

## 3. Lessons that apply directly
1. **Promote on relevance, including through connections** (Legion, URR, Dwarf Fortress).
2. **Generate from whatever is fixed first** (Legion). A request pins traits; the rest derives.
3. **Household-first population synthesis** (IPF, SPEW).
4. **Spend variation where eyes go:** head, hair, upper body, colour, accessories (McDonnell).
5. **Bounded, convex, correlated parameter spaces, and corner tests** for never-fail bodies and
   faces (morphable models, MetaHuman, Bannerlord, Dwarf Fortress).
6. **Pool and re-dress** visible characters (AC Unity); never allocate per person.
7. **Tag everything:** Census's hardest work was data tagging: "simply getting all the tagging
   information into the world was a tremendous feat" (Christopher Dragert). Our
   occupations, buildings, outfits and schedules must share tags from the start.
8. **Watch for stereotype lock-in:** Legion moved away from occupation-first generation because
   it produced "full-on stereotypes", and deliberately adds non-obvious traits that are then
   explained. Our occupation-first chain needs the same counterweight: a share of traits
   generated independently, then rationalised (the Caves of Qud move).
9. **Voices and barks multiply:** Legion recorded each line 20+ times and formant-shifted them.
   Our `voice` trait should drive TTS pitch, rate and roughness, or a modulation filter.
10. **Memory and opinion propagate** through relationships (Legion). The interpersonal phase
    needs the relationship graph to be derivable for anyone, not only the uprezzed.

## 4. Where our design goes beyond what exists
Stated carefully: large populations exist (Legion 9M, URR 10M, SPEW billions), and so do deep
characters (Dwarf Fortress histfigs, Legion's uprezzed). What we did not find in any single
system is the combination:
- **every** resident has a permanent identity and address, regenerated identically at any time
  from a hash, with **no storage** unless the player changes them (Legion discards its background
  people; Dwarf Fortress makes unnamed people on the spot and forgets them);
- full 3D bodies, faces and clothing **generated per person from parameters**, rather than chosen
  from a bank of variants (AC Unity's bulk crowd uses 29);
- a data-driven, extensible trait schema in which adding a characteristic provably leaves
  every existing person unchanged;
- a coherent art direction (Ghibli) imposed on the generated space, with measured colour and
  proportion rules.

Each piece has precedent; the combination does not appear to. It is the "notable" part, and
also where the risk sits: oatmeal (perceptual sameness) and soup (incoherence) at a scale where
nobody can review every person by hand. That is why the validation tooling matters as much as
the generator.

---

## Sources
- Watch Dogs: Legion:
  - [gamedeveloper.com, "How Watch Dogs: Legion's 'Play as Anyone' simulation works"](https://www.gamedeveloper.com/design/how-watch-dogs-legion-s-play-as-anyone-simulation-works);
  - [Ubisoft, "The Tools That Built London"](https://news.ubisoft.com/en-us/article/4po3S9Pwp1YcgBmGPmQxAh/watch-dogs-legion-the-tools-that-built-london);
  - [GDC Vault, Census talk (Dragert 2021)](https://www.gdcvault.com/play/1027018/Census-The-Systemic-Backbone-Behind);
  - [Engadget (nearly 9 million characters)](https://www.engadget.com/2019-06-10-watch-dogs-legion-e3-first-look.html).
- Ultima Ratio Regum:
  - Johnson, M. R. (2015), "Modelling Cultural, Religious and Political Affiliation in AI Decision-Making", AISB [local];
  - Johnson (2016), "Procedural Generation of Linguistics, Dialects, Naming Conventions and Spoken Sentences", DiGRA-FDG [local].
- Dwarf Fortress: [wiki: Historical figure](https://dwarffortresswiki.org/index.php/Historical_figure); [Creature token: appearance modifiers](https://dwarffortresswiki.org/index.php/Creature_token).
- Cities: Skylines: Steam and Paradox dev-diary discussions of the 65,536 agent limit; [80.lv on Cities: Skylines II](https://80.lv/articles/cities-skylines-2-doesn-t-have-limit-for-people-it-can-track).
- Assassin's Creed Unity: [Cournoyer, "Massive Crowd on Assassin's Creed Unity: AI Recycling", GDC 2015](https://gdcvault.com/play/1022141/Massive-Crowd-on-Assassin-s); [GameSpot on the 30,000-person crowds](https://www.gamespot.com/articles/assassins-creed-unity-can-support-crowds-of-30-000/1100-6421542/).
- Hitman: [Fauerby, "Crowds in Hitman", GDC 2012](https://gdcvault.com/play/1016443/Crowds-in-Hitman).
- Crusader Kings III: Steam discussions of character counts and pruning.
- Shadow of Mordor: [PC Gamer on the Nemesis system](https://www.pcgamer.com/uk/why-hasnt-anyone-copied-shadow-of-mordors-nemesis-system).
- Crowd perception:
  - McDonnell et al. (2008), "Clone Attack! Perception of Crowd Variety", ACM TOG 27(3);
  - McDonnell et al. (2009), "Eye-catching Crowds: Saliency based selective variation", ACM TOG 28(3);
  - Thalmann et al. (2009), crowd simulation [local].
- Randomness and variety:
  - Eiserloh (2017), ["Noise-Based RNG", GDC](https://gdcvault.com/play/1024365/Math-for-Game-Programmers-Noise);
  - Compton, "10,000 bowls of oatmeal", via [Emily Short](https://emshort.blog/2016/09/21/bowls-of-oatmeal-and-text-generation/).
- Population synthesis:
  - Beckman, Baggerly & McKay (1996);
  - Gallagher et al. (2017), [SPEW](https://arxiv.org/pdf/1701.02383) [local].
- Shape models:
  - Blanz & Vetter (1999), "A Morphable Model for the Synthesis of 3D Faces", SIGGRAPH;
  - Allen, Curless, Popović & Hertzmann (2006), "Learning a correlated model of identity and pose-dependent body shape variation" [local];
  - [SMPL](https://smpl.is.tue.mpg.de/);
  - [MetaHuman Creator](https://www.epicgames.com/site/en-US/news/announcing-metahuman-creator-fast-high-fidelity-digital-humans-in-unreal-engine).
- Animation: Hecker et al. (2008), "Real-time Motion Retargeting to Highly Varied User-Created Morphologies", ACM TOG 27(3) [local].
- Narrative: Ryan (2018), *Curating Simulated Storyworlds* ([Emily Short's reading notes](https://emshort.blog/2019/05/21/curating-simulated-storyworlds-james-ryan/)); [Grinblat, "Procedurally Generating History in Caves of Qud", GDC 2018](https://gdcvault.com/play/1024990/Procedurally-Generating-History-in-Caves); Short & Adams (eds.), *Procedural Generation in Game Design* (CRC 2017).
