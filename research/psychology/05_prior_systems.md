# 5. Prior systems: who has built this, and what we take

## 5.1 Knowledge and gossip
- **Talk of the Town** (Ryan, Summerville, Mateas & Wardrip-Fruin, AIIDE 2015; [paper](https://ojs.aaai.org/index.php/AIIDE/article/view/12825);
  local copy in `reference/papers/psychology/`).
  - About 200 NPCs, simulated over decades, form **mental models** of people and places. Each
    model is made of **belief facets**, each with value, predecessor, accuracy, **evidence list**
    and **strength**.
  - Nine **evidence** types in four categories:
    - how knowledge originates: reflection, observation, transference, confabulation, lie;
    - how it propagates: statement, eavesdropping;
    - how it deteriorates: mutation;
    - how it terminates: forgetting.
  - **Salience** (relationship to the observer, friendship, romance, job prestige, attribute type)
    decides what is noticed, told, misremembered and forgotten.
  - In conversation, the n most salient subjects come up. n is set by tie strength and
    **extraversion**.
  - Evidence strength decays with time. For statements it scales with the hearer's **affinity**
    for the source and the source's own belief strength.
  - Beliefs are revised when contrary evidence outweighs them. Every retelling strengthens the
    teller's own belief.
  - Every piece of evidence records **source, location and time**, so any rumour's path can be
    traced after play.
  - **We take:** belief facets with evidence and strength; the evidence typology, reduced to
    witness, told, overheard, public, lie and misremembered; salience; and source tracing (the
    `K.source` chain, which lets an NPC say *who* told them).
  - **We change:** Talk of the Town simulates eagerly for 200 people. We need **100,000+,
    generated on contact**, so our propagation is **lazy and deterministic** (06 §4) and gives the
    same answers.
- **Dwarf Fortress** (Tarn Adams, as reported in the paper above).
  - A **rumour** system: witnessed events, especially crimes, create rumours at local and regional
    level. Travellers (diplomats, caravans) carry them to new places.
  - Characters lie: false witness reports to a sheriff, and hiding opinions out of fear.
  - Personality has **facets** (0–100 in seven reported bands; 40–60 is unremarkable), plus
    **beliefs** (values), **needs** and **thoughts/memories** that drive stress
    ([DF wiki](https://dwarffortresswiki.org/index.php/Facet)).
  - **We take:** travellers as bridges between settlements; people reporting only facets that are
    out of the ordinary (the 40–60 band says nothing, which keeps prompts short); and needs and
    memories driving stress.

## 5.2 Social physics and social practices
- **Comme il Faut / Prom Week** (McCoy, Treanor, Samuel, Reed, Mateas & Wardrip-Fruin).
  - A "social physics" of about **5,000 rules**, authored by watching recurring patterns in films
    and TV.
  - **Social exchanges** (an intent, preconditions, influence rules that weigh desire, then
    outcomes that update relationships and a record of past events) make relationships playable
    ([Prom Week](https://promweek.soe.ucsc.edu/?p=101); [CiF paper](https://cs.uky.edu/~sgware/reading/papers/mccoy2014cif.pdf)).
  - **We take:** social exchanges as the unit of NPC–NPC and NPC–player interaction, and influence
    rules as weighted token predicates.
  - **We avoid:** Prom Week's characters are omniscient; ours know only what reached them.
- **Versu** (Evans & Short 2014, *IEEE TCIAIG*).
  - **Social practices**, the successors of Schank's scripts, are reactive joint plans (a meal, a
    greeting, a quarrel). They offer **affordances** to participants but never control them. Each
    agent chooses by utility ([paper](https://www.cs.uky.edu/~sgware/reading/papers/evans2014versu.pdf)).
  - **We take:** conversations and public scenes run as practices that offer beats. The NPC's
    stance (06 §5) picks among them. This fits the existing quest engine's "roles with
    eligibility conditions" (`research/questing_engine/quest_engine_rules.md`).

## 5.3 Emotion engines
- **GAMYGDALA** (Popescu, Broekens & van Someren 2014, *IEEE Trans. Affective Computing*).
  - An OCC appraisal engine that sits between hand-coded affect and a full cognitive model. The
    developer declares NPC **goals** and annotates **events** with their effect on goals; the
    engine produces OCC emotions, including **fortunes-of-others** emotions through NPC–NPC
    relations.
  - It is efficient for large numbers of NPCs and independent of the game AI ([TU Delft](https://research.tudelft.nl/en/publications/gamygdala-an-emotion-engine-for-games)).
  - **We take:** this is the right weight class. We add standards (moral foundations) and
    attribution (intent).
- **FAtiMA** (Dias & Paiva), **PsychSim** and **Thespian** (Marsella, Pynadath et al.): fuller
  appraisal and theory-of-mind architectures. They are cited as depth references; too heavy for
  100,000 on-contact characters.

## 5.4 Opinions, stress and memory in commercial games
- **Crusader Kings III.** **Opinion** is a sum of named, decaying **modifiers**. **Stress**
  accrues from acting against one's personality traits, and stress thresholds trigger **coping
  mechanisms** that shape relationships (irritable courtiers become rivals).
  **We take:** opinion as a sum of named modifiers, each with a source event and half-life (it
  explains itself in dialogue: "you helped my brother"); and stress from value-inconsistent acts
  leading to coping.
- **Middle-earth: Shadow of Mordor, the Nemesis system.** Named enemies **remember** earlier
  encounters and change tactics and talk. It shows that player-specific memory is the most
  noticeable form of reactivity.
  **We take:** NPCs who met the player store a **tiny memory delta**: their last opinion, promises,
  and a two-line summary of the talk.

## 5.5 LLM agents and keeping them in character
- **Generative Agents** (Park et al. 2023).
  - A **memory stream** of time-stamped observations; **retrieval** by recency × importance ×
    relevance; **reflection** into higher-level beliefs; and **planning**. 25 agents shared news,
    formed relationships and coordinated a party ([arXiv](https://arxiv.org/pdf/2304.03442v1)).
  - **We take:** retrieval scoring for which beliefs go into the prompt, capped at N.
  - **We avoid:** having the LLM *be* the simulation. That is too costly and non-deterministic at
    our scale, and our simulation is the token engine.
- **Personality in LLMs** (Serapio-García et al. 2023). Big Five personality in LLM output can be
  **measured reliably and shaped** by prompting with trait descriptions ([arXiv](https://arxiv.org/abs/2307.00184v4)).
  So trait **words** in the prompt are an effective control.
- **Persona drift.** LLM characters drift back toward "helpful assistant" over long
  conversations. Contradicting the world's lore is the top failure of LLM NPCs; the 2025 CPDC
  challenge and later work add psychology-grounded layers and consistency checks ([PersonaForge](https://preview.aclanthology.org/ingest-acl/2026.findings-acl.386/)).
  **We take:**
  - short conversations;
  - the **full token card** resent every turn (no drift from history);
  - a structured output format;
  - a **validator** that rejects replies revealing knowledge outside the card.

## 5.6 Finding the stories: story sifting
- **Felt / Winnow** (Kreminski et al.). Story sifting searches a simulation's event chronicle for
  "narratively potent sequences". Winnow patterns run **incrementally**, catching stories while
  they unfold ([Winnow](https://ojs.aaai.org/index.php/AIIDE/article/view/18903); [Felt](https://github.com/mkremins/felt)).
- **We take:** sifting patterns run over the event log, not over the whole population. When one
  matches (a betrayal followed by revenge, a newcomer saving a child), the quest engine is offered a
  storyline, cast from people with the right ties and knowledge.

## 5.7 Level of detail for simulation (Brom et al. 2007)
- Simulation LOD: "reduces quality of the simulation at the places unseen", in gradual steps, while
  keeping it plausible with minimum inconsistency ([IVE](https://artemis.ms.mff.cuni.cz/main/papers/IVE_IVA07.pdf)).
- **Our version is stronger.** Unseen places aren't simulated at a lower detail; they are
  **computed exactly on demand** from deterministic hashes. That has no inconsistency, because
  the answer never depends on whether anyone looked. It is the same principle as the existing
  generate-on-contact characters (`research/characters/procedural_npcs.md`).
