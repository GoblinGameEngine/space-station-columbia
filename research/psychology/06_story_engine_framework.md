# 6. The story engine framework

How an action by anyone, above all the player, reaches people by word of mouth and becomes each
person's own reaction, and then a line of dialogue. It is built on the research in files 01–05,
under the constraints of the existing character generator:
- hundreds of thousands of people;
- people generated **on contact**;
- **nothing stored except deltas**;
- everything **deterministic** from the world seed.

## 1. Design constraints
1. **Scale.** 100,000+ residents in about 1,000 settlements. Only the people near the player exist
   as nodes; everyone else is a pure function.
2. **Store only what the world cannot recompute:**
   - the **event log** of things that happened (mostly player-caused);
   - the few people the player actually met: their opinion, promises and a short memory.
3. **Consistency.** If Ada "told Bram", Bram's knowledge must name Ada as his source, and Ada must
   know it, in whichever order the player meets them.
4. **Degrees of separation.** An act touches the witnesses, then their close ties, then theirs.
   Each hop is weaker, and all of it is filtered through each person's personality and ties.
5. **Cheap at contact.** Computing a person's knowledge and reaction must fit in a few
   milliseconds on a worker thread. That is the same budget as today's L2 generation on contact.
6. **The LLM only voices.** Groq writes words for a situation the engine has fully decided. It
   never decides what a character knows or feels.

## 2. Tokens: how a character and a situation are written down
A **token** is a named, typed unit:
- a number 0..1 or −1..1;
- an enum;
- a short list;
- a reference to a person, place or event.

Tokens have **prefixes by area** (catalogue: `tokens.json`):

| prefix | area | source file |
|---|---|---|
| `ID.` | identity: pid, name, age, sex, life stage, household, settlement | existing L0 |
| `W.` | settlement culture, and the **role slot** (`W.role*`, next research round) | 03 |
| `P.` | personality: domains, facets, H, circumplex, attachment, if-then signature | 01 |
| `V.` / `M.` | values / moral foundations | 01 |
| `D.` | personality-disorder dimensions and severity | 02 |
| `C.` | frontier and space adaptation | 03 |
| `E.` / `F.` / `S.` | mood (PAD) / current emotions (OCC) / stress and coping | 01 |
| `R.` | ties: layer, kind, relational model, valence, power, trust, debt, grievance | 04 |
| `K.` | knowledge: beliefs about events, with source, hops, certainty and distortions; gossip traits | 04 |
| `EV.` | an event in the log | §3 |
| `X.` | the reaction: stance, intent, disclosure, tone | §5 |

**Three rules:**
1. **Derived, not stored.** Every `P`/`V`/`M`/`D`/`C`/`K`-trait token is a pure function of the
   stored L0–L2 traits, the person's hash stream and the settlement's `W` tokens.
2. **Bands for prompts.** Numbers are rendered as bands with words: very low / low / (omitted) /
   high / very high. Values between 0.4 and 0.6 are **omitted**, as Dwarf Fortress omits ordinary
   facets. That keeps a person's card to what is distinctive about them.
3. **Stable ids.** Token ids and enum names are the contract between the engine, the data files,
   the prompt compiler and the tests.

## 3. Events: the only history the world keeps
**An event** (`EV.`), about 40 bytes when packed:
```
EV.id       u32         sequential
EV.t        game minutes
EV.place    settlement id + (s, x)
EV.actor    pid | PLAYER | GROUP(id)
EV.verb     id from the verb taxonomy (data file)
EV.patients up to 3 pids (who it was done to or for)
EV.object   tag (item, building, animal, station system)
EV.mag      0..3 (trivial, minor, notable, major)
EV.intent   deliberate | careless | accidental | forced
EV.vis      public | private | secret
EV.claim    for statements: the event id or fact being asserted (lies included)
```

- **The verb taxonomy** is a data file, like `npc_traits.json`. Each verb is tagged with:
  - its **goal effects** on patients (harm, benefit, loss, gain);
  - its **moral foundations** touched, with sign (care, fair, loyal, auth, pure, lib);
  - its **relational-model** reading (a gift is CS or EM; a bribe is MP intruding on AR);
  - its **base salience**.

  Examples: help, rescue, give, trade, steal, damage, insult, praise, threaten, attack, lie,
  keep_promise, break_promise, trespass, tamper_life_support, return_lost, apologize, repay,
  spread_rumour.
- **Witnesses are computed, not stored.** They are everyone within sight at `EV.t`:
  - the NPCs live at the time;
  - anyone whose **deterministic schedule** (`schedule`: a pure `where(person, t)`) put them
    within sight radius of `EV.place`;
  - `EV.vis` secret narrows the set to the patients.
- **What gets logged:**
  - all player actions with `EV.mag` ≥ 1;
  - all player statements to NPCs about people or events;
  - world events the game creates (a fire, an accident, a wedding).
  
  At the rates the player can act, the log is small: kilobytes per play-hour. It is saved with the
  game.

## 4. Knowledge: who has heard, computed on demand
### 4.1 The social graph, generated from foci
- The **settlement graph** is built only when a person from that settlement is needed, and kept
  in an LRU cache.
- **Nodes:** its residents, from the households generator.
- **Edges:** from social foci (04 §4.2), each with `R.layer`, `R.kind` and `R.model`:
  - household (layer 5);
  - kin across households (5/15, from lineage);
  - workplace (15/50);
  - school class (15);
  - street and neighbours (50);
  - clubs, congregations and pubs (50);
  - a few weak acquaintance ties (150/500);
  - **inter-settlement bridges** for mobile roles.
- A tie inside a focus exists if `hash(seed, "tie", focus, min(a,b), max(a,b)) < p_focus ·
  homophily(a,b)`. Homophily covers age, occupation class, values and life stage.
- **Cost:** O(Σ focus size²) hashes per settlement, which is milliseconds for ~1,000 people.

### 4.2 Hearing, as a deterministic cascade
- Every potential telling `u → v` of event `e` at hop `h` (h = tellings since a witness) has:
  ```
  p_tell(u,v,e,h) = min(0.97, salience(e,u) · HEARSAY^h · gossip(u) · strength(layer(u,v)))
  live      ⇔ H(seed,"tell",e,u,v) < p_tell        -- the coin, fixed forever
  delay     =  −ln(1 − H(seed,"delay",e,u,v)) · days(layer)   -- exponential, mean by layer
  ```
  The prototype uses:
  - `HEARSAY` = 0.75;
  - `gossip` = 0.5 + 0.9·E − 0.3·C·H;
  - strength 0.9 / 0.7 / 0.45 / 0.25 and days 0.15 / 0.6 / 2.5 / 8 for layers 5 / 15 / 50 / 150.
- **Salience** of the event to the teller comes from:
  - `EV.mag` and the verb's base salience;
  - **prosocial-gossip** weight for norm violations (04 §4.9);
  - whether the teller cares about the patients or the actor (their ties);
  - the actor's prominence (the player, officials).
- **The public channel.** For heavy events (`EV.mag` ≥ 2), a virtual node PUBLIC (noticeboard, pub
  talk, station news) tells each person with `p = (weight − 0.75)·(0.5 + 0.6·E)` after about 1.5
  days. It is then a first hop like any other.
- **Person `x` knows `e` at time `t`** iff some path from a witness (or PUBLIC) to `x` of at most
  `MAX_HOPS` = 3 hops is all **live** and its delays sum to ≤ `t − EV.t`. The **earliest** such
  path gives `K.when`, `K.hops` and `K.source` (the last teller).
- **Why this is correct.** With the coins fixed in advance, the independent-cascade process is
  exactly reachability over live edges (Kempe, Kleinberg & Tardos 2003, Claim 2.3). Timing makes it
  continuous-time first-passage over the same live edges. So:
  - the **lazy query** (search backwards from `x`) gives *exactly* what a full simulation of
    everyone would give;
  - two people's answers are always consistent: if Bram heard it from Ada, Ada's own query finds
    she knew it earlier;
  - nothing is stored.
- **Verified by the prototype** (`tools/story/propagation_proto.py`, 600 people, 22 ties each):

  | event | lazy vs full-simulation disagreements | knows within 1d / 3d / 7d / 30d | lazy query cost |
  |---|---|---|---|
  | minor (a rude word) | 0 of 600 | 3% / 4% / 6% / 13% | median ~200 edge checks |
  | notable (a theft) | 0 of 600 | 2% / 7% / 10% / 24% | median ~490 |
  | major (a rescue, a fire) | 0 of 600 | 58% / 92% / 98% / 100% | median ~1,130 (the public channel adds a first hop from everyone) |

  The spread curves come from the structure (foci, layers, homophily, weak ties), not from
  hand-set percentages. Tuning uses the six constants above.

### 4.3 Distortion along the path (Allport & Postman)
The belief `x` holds is the event record transformed once per hop along its path. Each
transformation is a hash of (e, hop's teller, hearer):
- **Levelling:** optional fields (place, object, accomplices, time) each survive a hop with p ≈ 0.8.
  After six hops about 26% remain, matching the ~70% loss in the first 5–6 retellings.
- **Sharpening:** `K.mag` rises one step with p ≈ 0.15·(1 + (1 − H_teller) + E_teller)/2, and never
  falls.
- **Assimilation:** `K.intent` moves one step toward the hearer's **prior of the actor**. A
  distrusted actor's "accidental" becomes "careless", then "deliberate"; a liked one's moves the
  other way.
- **Lies:** a teller with `K.lie` (low H with a grievance against the actor, or a motive to shield
  someone) may substitute the actor or verb. The belief keeps `K.lied` = true for the game's own
  tracing, as in Talk of the Town. The hearer treats it as an ordinary statement.
- **Certainty:** `K.certainty` = 1 for witnesses, then × (0.9·trust(teller)) per hop.

### 4.4 Forgetting
Belief strength halves over a half-life set by salience, magnitude and memory (C). Below a floor
the belief is **forgotten**. A deterministic threshold draw per (e, x) decides when. Minor events
fade in days to weeks; major ones stay for years.

### 4.5 Across settlements
- Bridges are mobile roles and kin living elsewhere. They carry beliefs into another settlement's
  graph, where the cascade resumes from them at their hop count.
- The public channel covers the whole station only for `EV.mag` = 3 with `EV.vis` public
  (disasters, heroics).

## 5. Reaction: from what they know to how they act
At contact, for person `x`:
1. **Knowledge.** Query `K` for every relevant event:
   - events in x's settlement within the memory window;
   - events reachable over bridges;
   - public events.
2. **Appraisal (OCC).** For each belief, compute **desirability** and **praiseworthiness**.
3. **Emotions, opinion, grievances and stress.**
4. **Stance and intent.**

### 5.1 Appraisal
```
care(x,q)    = 1 if q = x;  else strength(layer) · sign(R.valence)   (0 if no tie)
desirab(x,b) = Σ_q goal_effect(verb,q) · K.mag · care(x,q)  +  Σ_v value_touch(verb,v) · V.v(x)
praise(x,b)  = Σ_f moral_tag(verb,f) · M.f(x) · K.mag · resp(K.intent)
resp         = deliberate 1.0 · careless 0.6 · accidental 0.2 · forced 0.1      (Weiner)
hearsay(b)   = K.certainty · 0.7^K.hops          (a witnessed act moves you more than a rumour)
```
- **Emotions** come from the signs (OCC):
  - toward the **actor:** admiration/reproach from `praise`; gratitude/anger when `praise` and
    `desirab` share a sign and x or someone x cares about is a patient;
  - **fortunes of others:** happy-for/pity for liked patients, gloating/resentment for disliked
    ones;
  - toward the **self:** joy/distress, fear if a threat to x's goals is likely to recur.
- **Personality gains:**
  - negative emotions × (0.6 + 0.8·N) × (1 + D.negaff);
  - pity and gratitude × (0.5 + A);
  - anger × (0.6 + 0.8·(1 − A)) × (1 + W.honor if the verb is an insult to x or kin);
  - gloating × (1 + D.antag);
  - everything × hearsay(b).

### 5.2 Opinion of the actor (usually the player)
- **Opinion is a sum of named modifiers**, as in Crusader Kings III. Each modifier has a source
  event and a half-life, so the NPC can say *why*:
  ```
  O(x,player) = Σ_j w_j · decay(t − t_j),   w_j < 0 counted × 2.5          (negativity bias)
  ```
- **Complex contagion gate.** A secondhand modifier counts toward the opinion only if the beliefs
  behind it arrived by at least `K.k_threshold` **independent first tellers**: 1 for the credulous,
  2 typically, 3 for skeptics. Below the gate it counts only as **wariness**, a separate small
  token.
- **Balance** (Heider). For each person q whom x cares about, and whom the player helped or
  harmed:
  ```
  O += 0.4 · care(x,q) · sign(act on q) · hearsay
  ```
  Enemies of x helped by the player count negatively.
- **Grievance** (McCullough). A deliberate harm to x or x's inner 15 opens `R.grievance` =
  {avoid, revenge, benevolence}. It decays at a rate set by A, H and closeness; apology and
  restitution events speed it; N (rumination) and `W.honor` slow it.
- **Stress.** Events against x's values or foundations, plus ICE stressors (`C.*`), add
  `S.stress`. Above a threshold, **coping** (by personality) changes behaviour, and
  **displacement** turns tension toward the settlement's `W.outgroup`, which is often the newcomer
  player (03 §3.2).

### 5.3 Stance and intent
Candidate stances: **warm, friendly, neutral, guarded, cold, hostile, afraid, ingratiating,
avoidant, confronting**. Each gets a score:
- the base from `O` and wariness;
- fear from the actor's perceived power and harm × N;
- **circumplex complementarity** with the player's approach: dominance pulls submission, warmth
  pulls warmth (01 §1.3);
- **CAPS if-then** modifiers whose situation features match now: public or private, authority
  present, kin involved, being asked for help, and so on;
- culture: `W.honor` for insults, `W.tight` for rule-breaking, `W.relmob` for how fast strangers
  are trusted;
- `D.*` and `S.coping`.

The highest score wins; ties are broken by hash.

The **intent** for the conversation (`X.intent`) comes from the stance plus the person's needs and
(later) **role**. Examples: thank, warn, accuse, ask for help, share news, test the player, sell,
keep away, recruit.

**Disclosure** (`X.disclose`) is which beliefs x will share with the player. It is set by trust in
the player, `K.gossip`, and whether sharing would incriminate x or someone x protects.

### 5.4 The if-then signature's situation features
A fixed list, so they can be matched cheaply:
`criticised_publicly`, `praised_work`, `child_in_danger`, `rule_broken`, `asked_for_help`,
`lied_to`, `authority_present`, `kin_involved`, `stranger_approach`, `talk_of_earth`,
`money_offered`, `threatened`, `apologised_to`, `own_mistake_raised`.

## 6. What is stored
| store | contents | size |
|---|---|---|
| event log | `EV` records, append-only, saved with the game | ~40 B per event |
| met people | per pid: opinion modifiers, grievance, promises, last stance, a 1–2 line memory of the talk (or tokens) | ~100–300 B each |
| caches | settlement graphs and query results (LRU) | not saved |

Everything else is recomputed identically. This is the same contract as the existing trait,
body and household generators.

## 7. Stories and quests
> The story layer (arcs, roles, beats, drama manager, chronicle) is specified in
> `research/story/04_arcs_in_the_engine.md`, with the catalogue in `research/story/story_types.json`.

- **Story sifting** (Felt/Winnow-style patterns, 05 §5.6) runs incrementally over the event log.
  Examples:
  - `harm(A,B) … revenge(B or kin(B), A)`;
  - `rescue(player, child(C)) … C's family meets player`;
  - `rumour_lie(spreader) … player confronts spreader`.
- A match offers the quest engine a storyline. Its roles are cast by **eligibility over tokens**
  (people who *know* X, have a grievance with Y, fit a relational model), as
  `quest_engine_rules.md` already specifies.
- **Player statements are events.** When the player tells someone a claim (true or not), it
  spreads through the same cascade as `EV.claim`. The player can warn, defend a reputation or
  sow a lie, and the network carries it, as in Talk of the Town's gameplay.

## 8. The prompt: tokens to Groq
**Assembly:** fixed order, with the static part first so the provider's **prompt cache** covers it.
Cached input is half price or less on Groq (see `research/npc_ai/llm_options.md`).

```
[WORLD]      Space Station Columbia · <settlement>, a <W.org> settlement, <W.age> years old ·
             culture: <W.indiv, W.honor, W.tight words> · <season/time/weather>
[PERSON]     <name>, <age>, <occupation / ROLE> · lives with <household summary>
             temperament: <banded P words, only non-ordinary: "sociable, blunt, quick to worry">
             values: <V.top> · cares about: <M top 2> · way with people: <P.style, P.att words>
             <D.facets as behaviour words, if any> · <C words: "came for the work, misses Earth">
             speech: <speech tokens: formality, verbosity, dialect>
[MOOD]       <E band words> · <F emotions ≥ threshold with intensity words> · stress: <S band>
[YOU AND THE STRANGER]  opinion: <O band> because <top 2 modifiers as short reasons>
             grievance: <R.grievance summary, if any> · promises: <open promises>
[WHAT YOU KNOW]  (only these; you know nothing else about recent events)
             - <belief rendered with source and certainty: "Heard from your neighbour Ada two
               days ago that the stranger broke into the mill at night. You half believe it.">
[THIS MOMENT] where, who else is present, what the stranger just said or did
[STANCE]     <X.stance>, wants to <X.intent> · will share: <X.disclose ids> · won't mention: <…>
[RULES]      Speak only as <name>. 1–3 sentences. Never state facts outside WHAT YOU KNOW; if
             asked, say you don't know or only heard rumours. No narration.
             Reply as JSON: {"say": "...", "tone": "...", "shared": [ids], "intent": "..."}
```

- **The validator:**
  - parse the JSON;
  - `shared` must be a subset of `X.disclose`;
  - reject lines naming people, places or events that are neither in the card nor in shared
    knowledge (a cheap named-entity check against the card's names);
  - on failure, retry once with a stricter note, then fall back to a template line built from the
    tokens.
- **Offline or no key:** the same tokens drive **template barks** (one per stance × intent), so the
  engine works without the LLM.
- **Cost:** about 500–900 input tokens (most of them cached) and ~60 output tokens per line. That
  is within the budget in `llm_options.md`.

## 9. Roles (next research round)
The framework already reserves slots for roles:
- `ID.occupation`, which exists;
- `W.role*`: the roles a settlement needs (keeper of the air plant, doctor, teacher, preacher,
  shopkeeper, gossip hub, mayor, sheriff, drunk, outsider, …);
- a per-person **role** with duties, authority (`R.power` toward others) and a public prominence
  that feeds salience;
- role-specific verbs, standards and intents.

The roles research will fill these tokens. Nothing in §§3–8 needs to change for that.

## 10. Build plan (for later; research only now)
1. `NpcPsyche`: derive the `P/V/M/D/C/K` tokens from the stored traits. Pure functions, with
   Python parity like `traits.py`.
2. The settlement graph from foci, with an LRU cache. Tests: determinism, and symmetry of ties.
3. The event log and the verb taxonomy data file. Witnesses from schedules.
4. The lazy knowledge query, ported from the prototype, plus distortion and forgetting. Tests:
   **lazy == eager** on generated settlements, calibration bands, and the per-contact time budget.
5. Appraisal, opinion, grievance, stress and stance.
6. The prompt compiler, the validator and template fallbacks, wired to `NpcAI`.
7. Story sifting patterns, with hooks into the quest engine.

## 11. Open questions
- **Kinship across households.** Lineage generation is needed for the kin ties that carry the
  strongest reactions. This is a small research item, alongside roles.
- **Moving characters.** A person who moves settlements changes graphs. Schedules stay pure, so
  treat their old settlement as a bridge.
- **Player disguise and anonymity.** When witnesses don't recognise the player, the actor becomes
  "a stranger" with appearance facets. That gives ToTT-style identification gameplay.
- **Calibration against the fiction.** Spread rates should feel right in play. The six propagation
  constants and the public-channel threshold are the dials.
