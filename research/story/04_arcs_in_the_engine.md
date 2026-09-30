# 4. Story arcs in the engine: the player's history as a series of arcs

The psychology framework (`research/psychology/06_story_engine_framework.md`) decides what each
person knows, feels and wants. This layer adds **story**. It notices when what is happening is a
story, gives the people in it **roles** and a **beat**, paces the whole thing like a storyteller,
and records the player's history as a chronicle of arcs. Dialogue then knows not only "you are
angry at the stranger" but "you are the avenger, at the vow, and the tension is rising".

## 1. Story tokens (`ST.`)
All story points are tokens, and are added to `research/psychology/tokens.json`.

| token | meaning | from |
|---|---|---|
| `ST.type` | one of the 76 story types (`story_types.json`) | catalogue (03) |
| `ST.family` | bonds forming / tested / broken, harm & justice, power & community, self & change, quiet | catalogue |
| `ST.role` / `ST.actant` | this person's role in the arc and its Greimas actant (subject, object, sender, receiver, helper, opponent) | casting |
| `ST.beat` | the current beat (a Propp-style function) | the template |
| `ST.stage` | Freytag stage: intro, exciting, rise, climax, tragic, fall, suspense, resolution | the template |
| `ST.tension` | 0..1, the beat's tension | the template |
| `ST.value` | the value the arc turns (McKee), with its current polarity: trust/betrayal −, … | the arc state |
| `ST.shape` | the target emotional curve (Reagan): rags to riches, riches to rags, man in a hole, Icarus, Cinderella, Oedipus | the catalogue |
| `ST.mythos` | the outcome family (Frye): comedy, romance, tragedy, irony (or `faded`) | set at resolution |
| `ST.theme` | Egri's premise, which the dialogue may echo but never state | the catalogue |
| `ST.deed` / `ST.aware` | Aristotle's grid on harmful beats: done or undone × knowing or ignorant | the event and K |
| `ST.affect` | what the beat serves for the player: suspense, surprise or curiosity (Brewer & Lichtenstein) | knowledge asymmetry |
| `ST.promise` | a planted setup that needs a payoff (threat, vow, secret, object) | beats |
| `ST.quality` | the score in 02 §2.3 | computed |
| `ST.featured` | whether the drama manager is actively surfacing this arc | the drama manager |
| `ST.chorus` | for people outside the arc: their distance (hops) and the side they take by balance theory | propagation + balance |
| `ST.sequel` | a follow-on arc this one can open (friendship → betrayal, vengeance → feud, rescue → mentorship) | the catalogue |
| `ST.storyteller` | the pacing personality: cassandra, phoebe, and later a Ghibli-toned one | a game setting |
| `ST.chronicle` | the player's history: an ordered list of arc summaries | the arc log |

## 2. The life of an arc
1. **Sifting (detection).** Patterns over the **event log**, the **knowledge** results and the
   **token states** (opinion thresholds, grievances, stress, ties) propose candidate arcs. Examples:
   - a harm to someone whose close tie has low A and knows of it → `vengeance`;
   - a player misdeed known to at least 12% of a settlement → `rumour_run_wild`;
   - a community crisis while many residents already dislike the newcomer → `scapegoat`;
   - two acts of kindness to the same person → `friendship`.
   
   Sifting runs incrementally, as each event or knowledge arrival comes in, in the Winnow style.
2. **Casting.** Roles are filled by **eligibility over tokens** (the catalogue's `eligible`
   strings), exactly as the quest engine casts aliases. The player can hold any role: subject,
   helper, opponent, object, or just a witness.
3. **Merging.** A candidate with the same **key** as a live arc joins it, rather than starting a
   parallel one. All rumours about the player make *one* reputation arc; all grievances of one
   avenger make *one* vengeance.
4. **Admission.**
   - Candidates are ranked by `ST.quality`: stakes × closeness to the player × novelty × fit to the
     storyteller's current tension target.
   - Only a few are **featured** at once: 4 for cassandra, 3 for phoebe, with **one slot reserved
     for a quiet, kishōtenketsu arc**.
   - The rest run in the **background**. They still change opinions and knowledge; they just aren't
     pushed at the player. A background arc is promoted when a slot frees up.
5. **Beats.** Beats advance in two ways:
   - **world-triggered**: the beat happens when the world makes it true. The avenger *learns* when
     K arrives; *vows* when their opinion passes −0.8; a friendship *develops* after a third
     kindness;
   - **surfaced**: the drama manager chooses one beat a day to bring before the player, typically
     by having an NPC seek the player out, speak, or act. It picks the featured arc whose next beat
     brings tension nearest the storyteller's target.
6. **Fading.** An untended arc (no beat for about 20 days) **fades**. That is Frye's irony by
   neglect, and it is realistic: most grudges and flirtations just stop.
7. **Resolution.** The last beat sets `ST.mythos` from the world state, not by fiat:
   - vengeance ends in tragedy if the avenger's opinion is still very low, in comedy if an apology
     led to forgiveness, and in irony otherwise;
   - a scapegoat arc ends in comedy if the town's opinion recovered, and tragedy if not.
   
   It then writes **deltas** (Todorov's new equilibrium): tie changes, opinion modifiers, a role
   gained or lost, and a belief spread (the arc itself becomes news).
8. **Sequels.** A resolved arc can open another. Friendship then harm is betrayal; vengeance then
   retaliation is a feud; a rescue then a request for help is mentorship. This is how a history
   becomes a *series of arcs* rather than disconnected episodes. The prototype run showed it: the
   player befriended resident 355 (day 20) and later broke a promise to them (day 41). That opened
   a vengeance arc, which a sequel rule would type as `betrayal`.
9. **Chronicle.** Each finished arc becomes one line of `ST.chronicle`: day, type, roles, beats
   reached, mythos, deltas. This **is** the player's history. Story sifting over the chronicle
   finds the long arcs, the life story: the stranger who became the town's friend, or its villain.

## 3. Degrees of separation in a story
- **The principals** are the cast roles. They get the full `ST` card.
- **The chorus** is everyone the arc's events reached through propagation (1–3 hops). They get
  `ST.chorus`:
  - their **distance**;
  - their **side** by balance theory: the friend of the victim sides with the victim, the enemy of
    the avenger with the player, and so on;
  - how the story **reached them** (the source chain, distorted per hop).
  
  They don't play beats, but their dialogue colours accordingly. The chorus is how "characters
  degrees of separation apart are affected by others' actions".
- **Aristotle's weighting:** intensity scales with closeness. The same harm is gossip at three hops
  and a wound in the household.
- **The town's verdict**, the Spoon River chorus of "all the men loved him, most of the women
  pitied him", is the aggregate of chorus opinions. That is exactly the psychology framework's
  reputation, now tied to a named story.

## 4. The drama manager and the storytellers
- **What it does:** each day, pick at most one surfaced beat among featured arcs, targeting the
  storyteller's tension curve. This is Façade's beat manager at settlement scale.
- **The storytellers:**
  - **cassandra:** waves of tension, 3 conflict slots plus 1 quiet slot;
  - **phoebe:** long calm stretches, 2 conflict slots plus 1 quiet slot;
  - a **Ghibli-toned teller:** mostly kishōtenketsu, conflict rare and humane. It is the natural
    default for this game.
- **Balance rules:**
  - about three positive beats for each negative one, for the negativity bias;
  - no more than two tragedies in a row;
  - novelty: no story type repeated in the last three featured.
- **Surfacing hooks** (how a beat reaches the player):
  - an NPC with a role in the arc **seeks the player** (placement override in the population
    system);
  - an NPC **brings it up** in conversation (the `[STORY]` section, below);
  - a **world event** is injected (the air plant fails).

## 5. From story to dialogue: the `[STORY]` section of the prompt
It is added to the prompt card from psychology 06 §8, and holds only the arcs this NPC is in,
featured first, 1–2 at most:
```
[STORY]  You are the AVENGER in "a wrong to be repaid" (the stranger stole from your sister).
         Beat: the vow — you have decided to make it right; tension rising.
         You want: an admission, in front of others. Hold your anger until others are present.
         Theme to echo, never state: revenge feeds on itself.
         Others: your sister (the victim) wants it dropped; the smith sides with the stranger.
```
- The **beat maps to the reaction layer:**
  - `X.intent`: vow → test/accuse; pursuit → confront; reckoning → accuse or forgive;
    ketsu → thank/share;
  - `X.stance` bias, and what to disclose.
- The LLM gets the *dramatic situation*, not a script. It writes a line that plays that beat in
  that person's voice. The validator still enforces knowledge limits: an avenger at *learning*
  cannot mention details that didn't survive levelling.
- **Chorus members** get one line instead, for example: `[STORY] You've heard (third-hand) the
  stranger robbed the Pantier girl; you side with the Pantiers.`

## 6. The prototype: `tools/story/arc_proto.py`
A settlement of 400 generated people, 60 days, 62 player acts (a mostly decent player: help, gift,
return, sometimes an insult, a theft or a broken promise), and an air-plant failure on day 32.

| | cassandra | phoebe |
|---|---|---|
| arcs sifted / merged into existing | 43 / 10 | 43 / 10 |
| featured or finished | 12 | 15 |
| faded untended | 11 | 13 |
| history | friendships and lost-and-found stories completing as comedies, while vengeance arcs rise; a **scapegoat** arc after the crisis ends in **tragedy** | mostly quiet comedies; conflict held back |
| surfaced tension vs target | follows the waves | stays near the calm target, with one spike |

**What this shows:**
1. The same world and the same player make different histories under different storytellers. The
   drama manager shapes the *telling*, not the facts.
2. The **scapegoat arc emerges from the psychology layer**. Opinions formed by word of mouth plus
   a crisis produced "blame the newcomer" (Kanas's displacement) without it being authored.
3. Admission control and a reserved quiet slot are required. Without them the featured set fills
   with high-stakes conflict and quiet arcs starve, which is wrong for a Ghibli-toned game. Both
   failures were seen and fixed during the prototype run.

## 7. What is stored
| store | contents | size |
|---|---|---|
| arc instances (live and background) | type, key, roles (pids), beat, beat log, quality, promises | ~100–200 B each; a few dozen live |
| the chronicle | finished arcs: day, type, roles, mythos, deltas | ~60 B per arc |

Everything else, including chorus sides, distortions and stances, is recomputed on contact as in
the psychology framework.

## 8. Build plan (after the roles research)
1. Load `story_types.json`, and compile the `eligible` strings into token predicates.
2. Sifting patterns, incremental over the event log and knowledge arrivals; include sequel rules.
3. Arc instances, merging, admission, and world-triggered and surfaced beats; the storytellers.
4. The `[STORY]` prompt section and the beat → intent/stance mapping.
5. The chronicle, and long-arc sifting over it.
6. Tests: determinism, admission and quiet slots, fading, and calibration against the prototype.

## 9. Open questions
- *Roles are now researched* (`research/roles/`): role hooks, vacancies and contested informal roles feed sifting and casting.
- **Roles** (next round) will add many role-specific eligibilities and sifting triggers (the
  sheriff pursues, the preacher counsels, the editor spreads the story).
- **Tone of the default storyteller.** It needs tuning against the Ghibli research: how rare and
  how gentle conflict should be.
- **Player-authored stories.** The player's statements (psychology 06 §7) can start arcs,
  deliberately or not: a lie starts a `rumour`, a confession a `remorse`.
