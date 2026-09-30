# 1. Personality: models, tokens and generation

What each model contributes, which tokens it becomes (prefix `P.`, see tokens.json), and how to
generate it. The game already stores the Big Five plus warmth, humour, courage, honesty and
curiosity (`npc_traits.json`, trait `personality`, layer L2). Everything below either derives from
those or adds a few more stored numbers.

## 1.1 The Five-Factor Model and its facets
- **The model.** The Big Five, as operationalised by Costa & McCrae's NEO PI-R (1992): 240 items,
  **30 facets**, six per domain.
  - **Neuroticism (N):** anxiety, angry hostility, depression, self-consciousness, impulsiveness,
    vulnerability.
  - **Extraversion (E):** warmth, gregariousness, assertiveness, activity, excitement-seeking,
    positive emotions.
  - **Openness (O):** fantasy, aesthetics, feelings, actions, ideas, values.
  - **Agreeableness (A):** trust, straightforwardness, altruism, compliance, modesty,
    tender-mindedness.
  - **Conscientiousness (C):** competence, order, dutifulness, achievement striving,
    self-discipline, deliberation.
  
  ([NEO PI-R](https://psychology.fandom.com/wiki/NEO_Personality_Inventory); [Costa & McCrae scoring notes](https://post.ca.gov/portals/0/post_docs/publications/psychological-screening-manual/NEO_PI-R.pdf))
- **Why facets.** The domains say *how much*; the facets say *which way*. A high-N person who is
  mostly *angry hostility* reacts to an insult quite differently from one who is mostly
  *self-consciousness*. We do not need all 30 as stored numbers. **Derive each facet as its
  domain plus a small hashed offset** (sd 0.08). Only the facets the story engine reads get
  tokens: anxiety, angry hostility, vulnerability, gregariousness, assertiveness, trust,
  straightforwardness, altruism, compliance, modesty, dutifulness and deliberation.
- **Tokens:**
  - `P.O`, `P.C`, `P.E`, `P.A`, `P.N`: the domains, 0..1 (already stored);
  - `P.f.<facet>`: derived facets, 0..1.

## 1.2 HEXACO's sixth factor: Honesty-Humility
- **The model.** Ashton & Lee's HEXACO adds **Honesty-Humility (H)**, with four facets:
  sincerity, fairness, greed avoidance and modesty. High-H people "avoid exploiting others for
  their own benefit, rarely feel inclined to break rules" ([HEXACO](https://en.wikipedia.org/wiki/HEXACO_model_of_personality_structure)).
- **Why we need it.** It is the axis the Big Five blur: who lies, cheats, takes a bribe or spreads
  a self-serving rumour. The existing `honesty` value becomes `P.H`.
- **Tokens:** `P.H`, plus the derived facets `P.f.sincerity`, `P.f.fairness` and `P.f.greed`.

## 1.3 The interpersonal circumplex: how someone behaves toward others
- **The model.** Two orthogonal axes: **agency** (dominance, status, control) and **communion**
  (warmth, friendliness) ([interpersonal circumplex](https://en.wikipedia.org/wiki/Interpersonal_circumplex)).
- **Complementarity.** In interaction, "dominant behavior pulls for submissive behavior and vice
  versa, whereas warmth pulls for warmth and coldness pulls for coldness". This is a
  ready-made rule for how an NPC answers the player's tone.
- **Derivation.**
  - `P.agency` ≈ 0.5·assertiveness + 0.3·E + 0.2·(1 − A.compliance).
  - `P.communion` ≈ 0.5·warmth + 0.3·A + 0.2·E.warmth.
  - Both are shifted by the character's role (status) once roles are researched.
- **Tokens:** `P.agency`, `P.communion`, and the octant name `P.style`: assured-dominant,
  arrogant-calculating, cold-hearted, aloof-introverted, unassured-submissive, unassuming-ingenuous,
  warm-agreeable or gregarious-extraverted.

## 1.4 Values: what a person wants from life (Schwartz)
- **The model.** Schwartz's **10 basic values**: self-direction, stimulation, hedonism,
  achievement, power, security, conformity, tradition, benevolence and universalism. They sit in
  a *circle*: neighbouring values are compatible, opposite ones conflict, and the structure is
  near-universal across cultures ([theory of basic human values](https://en.wikipedia.org/wiki/Theory_of_basic_human_values)).
  The 2012 revision refines this to 19 values.
- **Why.** Values are the **goals** in OCC appraisal (§1.8). An event helps or harms what a person
  values. A security-first grandmother and a stimulation-first teenager react oppositely to the
  same stunt.
- **Generation.** Draw a point on the circle (a preferred direction) and a strength, then give
  each value a weight that falls off with circular distance. This automatically keeps the
  circle's compatibilities.
  - Personality correlations: O leans toward self-direction and stimulation, A toward
    benevolence, C toward conformity and security, low H toward power.
  - Age drifts toward tradition, conformity and security.
- **Tokens:** `V.<value>`, 0..1 each, and `V.top` (the top two, for prompts).

## 1.5 Moral foundations: what a person counts as right and wrong (Haidt & Graham)
- **The model.** Six intuitive foundations: **care/harm, fairness/cheating, loyalty/betrayal,
  authority/subversion, sanctity/degradation, liberty/oppression** ([Moral Foundations Theory](https://moralfoundations.org/)).
- **Why.** These are the **standards** in OCC appraisal. Each action verb in the event taxonomy
  (06 §2) is tagged with the foundations it touches, and a witness's weights scale how
  blameworthy or praiseworthy they find it. Breaking a station rule offends an authority-heavy
  character. Letting someone down offends a loyalty-heavy one.
- **Generation:**
  - care from A and warmth;
  - fairness from H;
  - loyalty and authority from C and tradition;
  - sanctity from tradition, and from low O;
  - liberty from self-direction and the frontier individualism of the settlement (03).
- **Tokens:** `M.care`, `M.fair`, `M.loyal`, `M.auth`, `M.pure`, `M.lib`, 0..1.

## 1.6 Attachment: how a person holds relationships (Bartholomew & Horowitz 1991)
- **The model.** Two dimensions: the model of **self** (anxiety) and the model of **others**
  (avoidance). They give four styles ([Bartholomew & Horowitz 1991](https://pubmed.ncbi.nlm.nih.gov/1920064/)):
  - **secure:** positive self, positive others;
  - **preoccupied:** negative self, positive others; worries about relationships;
  - **dismissing:** positive self, negative others; stresses independence;
  - **fearful:** negative self, negative others; avoids closeness for fear of rejection.
- **Why.** Attachment sets how ties react to strain. When something threatens a close tie,
  preoccupied people pursue, dismissing people withdraw and fearful people do both. It also sets
  how fast trust in a newcomer (the player) grows.
- **Generation:**
  - `P.att_anx` ≈ 0.6·N.vulnerability + noise;
  - `P.att_avoid` ≈ 0.5·(1 − E.warmth) + 0.3·(1 − A.trust) + noise;
  - childhood backstory tokens can shift both, once written.
- **Tokens:** `P.att_anx`, `P.att_avoid`, `P.att` (the style name).

## 1.7 Temperament and mood: PAD (Mehrabian)
- **The model.** **Pleasure, Arousal, Dominance.** A temperament is a person's *average*
  emotional state. Moods and emotions are displacements from it.
- **Mapping from the Big Five** (Mehrabian 1996): extraversion is mainly dominant and secondarily
  pleasant; agreeableness is pleasant, arousable and submissive; conscientiousness is pleasant and
  dominant in equal parts ([PAD analysis](https://www.cs.uky.edu/~sgware/reading/papers/mehrabian1996analysis.pdf)).
  Neuroticism maps to unpleasant and arousable.
- **Why.** PAD is the continuous **mood state** the engine tracks. A few emotion events push it,
  and it relaxes back toward temperament with a half-life. It colours tone words in the prompt
  and gates behaviour: low P with high A gives snapping, low D gives appeasing.
- **Tokens:** `E.P`, `E.A`, `E.D` for the current mood, and `E.P0`, `E.A0`, `E.D0` for
  temperament, derived and never stored.

## 1.8 Emotion from appraisal: the OCC model
- **The model.** Ortony, Clore & Collins distinguish **22 emotion types**. All of them are
  valenced reactions to three things ([OCC summary](https://arxiv.org/pdf/2307.10031); [logic of OCC](https://www.cs.uky.edu/~sgware/reading/papers/adam2009logical.pdf)):
  - **events**, judged by their consequences for one's **goals**: joy/distress, hope/fear,
    satisfaction/disappointment, relief/fears-confirmed; and the *fortunes of others*: happy-for,
    pity, gloating, resentment;
  - **agents' actions**, judged against **standards**: pride/shame, admiration/reproach, and the
    compounds gratitude/anger and gratification/remorse;
  - **objects**, judged by **tastes**: love/hate.
- **Intensity** comes from desirability, praiseworthiness and appeal. OCC is the standard basis of
  game emotion engines (GAMYGDALA, FAtiMA; see 05).
- **Why.** It is exactly the bridge from "who did what to whom" to "how this person feels", and
  it naturally covers **degrees of separation**. The *fortunes-of-others* branch is how an event
  that happened to your friend makes *you* feel (happy-for or pity), or to your rival (gloating or
  resentment). Its weight is the tie between you and that person (04).
- **Tokens:** `F.<emotion>` with intensity 0..1, only for emotions currently above threshold
  (usually 0–3 per person): `F.anger`, `F.pity`, `F.gratitude`, `F.fear`, `F.admiration`, …

## 1.9 Personality as if-then signatures: CAPS (Mischel & Shoda 1995)
- **The model.** A person is not a set of averages but "a set of if-then rules — if this
  situation, then that behavior". Two people with equal trait scores differ in *which*
  situations set them off ([CAPS](https://en.wikipedia.org/wiki/Cognitive-affective_personality_system)).
  The mediating units are encodings, expectations, affects, goals and values, and
  self-regulatory competencies.
- **Why.** This is the answer to "every character self-contained and unique" without authoring
  anyone. Traits set the *average* reaction. A small, hashed **signature** of 3–6 if-then
  modifiers gives each person a recognisable way of reacting.
- **Generation.** Draw a few situation features from a fixed list (06 §5.4), for example:
  - being criticised in front of others;
  - a child being in danger;
  - someone breaking a rule;
  - being asked for help;
  - being lied to;
  - authority being present;
  - one's work being praised;
  - talk about Earth or home.
  
  Draw each with a response modifier (+ or − on an approach/avoid/confront/ally stance). Weight
  the draws by trait: high N raises the chance of "criticised → defensive", high A of
  "help asked → eager".
- **Tokens:** `P.if` is a short list of `feature→response` pairs. The prompt only gets the ones
  that match the current situation.

## 1.10 Two more things the story engine needs from the mind
- **Needs and stress**, as in Crusader Kings III and Dwarf Fortress (05): accumulated strain from
  events that cut against the person's values or foundations.
  - Stress relaxes over days. Past a threshold, the person falls back on **coping** behaviour
    chosen by personality: withdraw, drink, lash out, pray, work harder, confide.
  - Isolation and the ICE stressors in 03 feed it.
  - **Tokens:** `S.stress` (0..1) and `S.coping` (the style).
- **Gossip and discretion:** how likely the person is to pass news on.
  - It is derived: `K.gossip` = 0.5 + 0.9·E − 0.3·C·H, as in the prototype.
  - Honesty-humility and agreeableness set whether what they pass on stays accurate
    (`K.embellish`). Low H with a grievance gives *lying* (`K.lie`).
  - These drive the propagation of 06 §4.

## 1.11 Generation rules (summary)
1. The stored L2 numbers stay as they are: the Big Five plus warmth, humour, courage, honesty and
   curiosity, mid-weighted with sd 0.17.
2. Everything else is a **pure function** of those numbers, the person's hash stream, age, sex and
   (later) role. Nothing new is stored, and a person regenerates identically.
3. **Correlations.** Draw the Big Five with the known small intercorrelations, rather than
   independently:
   - N with low A and low C: about −0.2 to −0.3;
   - E with O: +0.2;
   - A with C: +0.2.
4. **Age trends (maturity):** A and C rise, N falls with age; E and O fall slightly in old age.
5. The **tails** carry character. As in Dwarf Fortress, most people are ordinary and a few are
   extreme; the extremes are where the personality-disorder dimensions (02) begin.
