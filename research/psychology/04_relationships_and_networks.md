# 4. Relationships, networks and degrees of separation

How people are tied, how far influence travels, and how news of an action changes as it moves.
Tokens: `R.` for a tie (an edge between two people), `K.` for knowledge (a belief about an
event).

## 4.1 How many ties, and how close: Dunbar's layers
- People's networks come in **discrete layers**, each about **three times** the size of the last:
  **~5** (support clique), **~15** (sympathy group), **~50** (band), **~150** (active network),
  and ~500 and ~1,500 beyond (Zhou, Sornette, Hill & Dunbar 2005, *Proc. R. Soc. B*: "a
  geometrical series approximating 3–5, 9–15, 30–45", scaling ratio ≈ 3; [arXiv](https://arxiv.org/abs/cond-mat/0403299)).
- Closeness, contact frequency and willingness to help fall with each layer.
- **For us:**
  - `R.layer` ∈ {5, 15, 50, 150, 500} is the backbone of a tie. It sets **strength** and **talk
    frequency**: in the prototype, strength 0.9 / 0.7 / 0.45 / 0.25 and mean days between
    conversations 0.15 / 0.6 / 2.5 / 8.
  - Each person's layers are filled to about Dunbar's sizes. Extraverts run fuller outer layers;
    the inner five stays about the same for everyone.

## 4.2 Where ties come from: social foci (Feld 1981)
- **Focus theory.** Ties form around **foci**: "neighborhoods, … the tight groupings of close
  families", workplaces, classes, clubs. People meet repeatedly inside them, and a small,
  constraining focus (a team, a class) makes ties more reliably than a large loose one (Feld 1981,
  *AJS* 86(5):1015–1035; [summary](https://scinapse.io/papers/1977186326)).
- **For us, this is the generator.** A settlement's social graph is built **on demand** from its
  foci:
  - households, from NpcHouseholds;
  - kin across households, from lineage (future kinship research);
  - workplaces, from occupations plus places;
  - streets and neighbouring buildings;
  - school classes, by age;
  - congregations, clubs and the pub, weighted by E and values.
  
  Within a focus, a tie exists if a **symmetric pair hash** falls under the focus's tie
  probability times **homophily**. So it is deterministic, needs no storage and is the same from
  either end.

## 4.3 Who ties to whom: homophily (McPherson, Smith-Lovin & Cook 2001)
- "Similarity breeds connection": marriage, friendship, work, advice, support and information ties
  are all homogeneous. The strongest divides are race and ethnicity, then age, religion,
  education, occupation and gender. Information that flows through networks therefore stays
  **localized**, and "distance in terms of social characteristics translates into network
  distance" ([Annual Review of Sociology](https://pdodds.w3.uvm.edu/files/papers/others/2001/mcpherson2001.pdf)).
- **For us:** the tie probability inside a focus is multiplied by a similarity kernel (age,
  occupation class, values, life stage). A side effect is that news stays within a social stratum
  unless a bridge carries it.

## 4.4 Bridges: the strength of weak ties (Granovetter 1973)
- The overlap of two people's networks grows with the strength of their tie. Weak ties are
  **bridges** between otherwise separate clusters, and "no strong tie is a bridge"
  ([paper](https://www.cs.umd.edu/~golbeck/INST633o/granovetterTies.pdf)).
- **For us:**
  - the 150/500-layer acquaintances, plus **mobile roles** (drivers, traders, doctors, clergy,
    postal workers), are how news crosses between groups and between settlements;
  - like Dwarf Fortress's caravans and diplomats (05), these people carry rumours between
    settlements;
  - they get an inter-settlement edge set.

## 4.5 What kind of relationship: Fiske's four relational models, and Wish, Deutsch & Kaplan
- **Relational Models Theory (Fiske 1992)** has four elementary forms ([IEP](https://iep.utm.edu/r-models/)):
  - **Communal Sharing:** "we are one", in family and close friends; sharing without counting;
  - **Authority Ranking:** hierarchy, as between boss and worker, or elder and young;
  - **Equality Matching:** balanced turns, favours returned, one person one vote;
  - **Market Pricing:** ratios and value, as in trade and wages.
- Each model defines what counts as a **violation**. Keeping score of a communal gift offends; an
  unreturned favour offends under Equality Matching; disobedience offends under Authority Ranking.
  So the model decides how an action is judged *within* the tie.
- **Wish, Deutsch & Kaplan (1976)** found four perceived dimensions of any relationship:
  cooperative-friendly ↔ competitive-hostile, equal ↔ unequal, intense ↔ superficial, and
  socioemotional-informal ↔ task-oriented-formal ([summary](https://mediate.com/what-are-the-fundamental-dimensions-of-social-relationships/)).
- **For us:**
  - `R.model` ∈ {CS, AR, EM, MP}, from the focus (household → CS, work → AR/MP, neighbours → EM,
    shop → MP).
  - `R.valence` (−1..1), `R.power` (−1..1, their agency relative to ours), `R.intensity` (the
    layer) and `R.formal` (0..1).

## 4.6 How ties pull on each other: structural balance (Heider; Cartwright & Harary 1956)
- Triads tend toward consistency: a friend of a friend is a friend, the enemy of a friend an enemy,
  the friend of an enemy an enemy, and the enemy of an enemy a friend. A triad is balanced when the
  **product of its signs is positive**, and balanced networks split into two camps
  ([Cartwright & Harary via review](https://arxiv.org/pdf/1803.02082)).
- **For us:** this is the rule for how **the player's relationship with one person moves another
  person's opinion** of the player:
  - helping my friend earns warmth;
  - befriending my enemy earns suspicion;
  - harming my enemy earns a guilty approval.
  
  It is applied to opinions at contact time, with each hop damped (§4.8).

## 4.7 How far influence travels: three degrees, and the critique
- **Christakis & Fowler.** In the Framingham network (4,739 people), happiness is associated across
  **up to three degrees**. When a friend's friend becomes happy your chance of being happy rises
  about 10%, and 5.6% at the third degree; they found similar patterns for obesity and smoking
  ([BMJ 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC2600606/)).
- **The critique.** Lyons (2011) argued the statistics do not support causal transmission: the
  methods were flawed, and homophily and shared environment are confounds ([arXiv](https://arxiv.org/pdf/1007.2876)).
- **For us:** "three degrees" is a sound **design horizon**, not a law of nature. We cap
  propagation at **3 hops** (`MAX_HOPS`) and make effects **fall off with each hop**. Anything that
  must travel further does so through the **public channel** (the noticeboard, pub talk, station
  news) or through bridges.

## 4.8 Simple and complex contagion (Centola)
- **Simple contagions** (information, disease) pass with **one contact**. **Complex contagions**
  (behaviour, norms, attitudes) need **reinforcement from several contacts**.
- In Centola's experiment, a health behaviour spread faster and further in **clustered** networks
  than in random ones ([MIT](https://news.mit.edu/2010/social-networks-health-0903)).
- **For us, this is the split between two kinds of spread:**
  - **Facts spread simply.** One telling is enough for someone to *know* the player did X.
  - **Attitudes spread complexly.** For secondhand information to move someone's **opinion** of
    the player, it must arrive by `k` independent routes. `k` = 1 for the credulous (high A,
    high N), 2 typically, and 3 for skeptics (high C, low A).
  - A direct witness counts as fully reinforced.
  - Result: one gossip can tell a town what you did, but only a cluster of friends agreeing turns a
    town against you, which is also realistic.

## 4.9 Gossip and reputation
- **About two-thirds of conversation is social**, mostly gossip; Dunbar likens it to grooming, a
  way to build coalitions ([Dunbar 2004](https://scinapse.io/papers/2110258639)).
- **Prosocial gossip.** People pass on negative information to *warn* others about untrustworthy
  people, and do it chiefly to help (Feinberg, Willer et al. 2012; [Berkeley](https://news.berkeley.edu/2012/01/17/gossip)).
- **Indirect reciprocity by image scoring** (Nowak & Sigmund 1998, *Nature*). Cooperation evolves
  when people help those with a good **image score**, a reputation raised by helping and lowered
  by refusing. It works only if the chance of knowing someone's image exceeds the cost/benefit
  ratio of helping ([IIASA](https://pure.iiasa.ac.at/5608)).
- **For us:**
  - `K.gossip` (1.10) sets how readily someone tells; salience sets what they tell.
  - **Negative, norm-relevant news spreads more readily** than neutral news (prosocial gossip),
    through a salience bonus for standard-violating events.
  - A settlement's **reputation** of the player is simply the image score as that community knows
    it. It isn't stored: the reaction step (06 §5) aggregates it from what each person knows.

## 4.10 How news changes as it travels: rumour (Allport & Postman 1947)
- In serial reproduction, about **70% of details were lost in the first 5–6 retellings**. Three
  processes act ([Rumor](https://en.wikipedia.org/wiki/Rumor)):
  - **levelling:** details drop out;
  - **sharpening:** a few details are kept and emphasised;
  - **assimilation:** the story is bent toward the teller's expectations and motives. In their
    example, a truck labelled TNT became "medical supplies".
- **For us:** every hop transforms the event record carried by a belief:
  - **Levelling:** each optional field (place, time, object, accomplices) survives a hop with about
    0.8 probability, so roughly 0.8⁶ ≈ 26% remain after six hops, matching the 70% loss.
  - **Sharpening:** the magnitude word may escalate (about 15% per hop), more so for low-H and
    high-E tellers.
  - **Assimilation:** attribution of intent bends toward the hearer's prior about the actor. A
    distrusted player's accident becomes "on purpose".
  - Lies are separate (`K.lie`): a deliberate substitution, and the only transformation a
    character knows they did.

## 4.11 Judging the act: attribution (Weiner) and negativity bias
- **Weiner's model:** event → **controllability** → **responsibility** → affect (**anger** if
  responsible, **sympathy** if not) → behaviour (reprimand or help) ([review](https://psychologie.uni-greifswald.de/storages/uni-greifswald/fakultaet/mnf/psychologie/Allgemeine_II/Publikationen/Reisenzein2015_Universality_Attribution_Affect_Model.pdf)).
  **For us:** events carry an `intent` token (deliberate, careless, accidental, forced). The
  hearer's belief about intent (after assimilation) selects between anger and reproach on one
  side and pity and sympathy on the other.
- **Negativity bias: "Bad is stronger than good"** (Baumeister et al. 2001). Bad events, feedback
  and impressions have more impact, form faster and resist disconfirmation more than good ones
  ([paper](https://fbaum.unc.edu/teaching/articles/Baumeister_2001.pdf)).
  **For us:** negative contributions to opinion are weighted about 2.5× positive ones, and decay
  more slowly (a longer half-life).

## 4.12 Getting over it: forgiveness (McCullough, TRIM)
- After a transgression, motivation moves along three dimensions: **avoidance**, **revenge** and
  (reduced) **benevolence**. Forgiving means avoidance and revenge falling and benevolence
  returning ([TRIM](https://ppc.sas.upenn.edu/node/223)).
- **For us:** a grievance token `R.grievance` = {avoid, revenge, benevolence}. It decays at a rate
  set by A, H and closeness, is sped up by apology or restitution events, and slowed by rumination
  (N) and honor culture (`W.honor`).
- It selects stance: avoidant NPCs keep away, vengeful ones seek payback or spread damaging gossip,
  and forgiving ones warm up.

## 4.13 Tokens (summary)
**Tie (`R.`)**, generated from foci. Only the deltas the player causes are stored:
`R.layer`, `R.kind` (kin, partner, household, friend, coworker, neighbour, classmate, congregant,
acquaintance, rival, authority), `R.model` (CS/AR/EM/MP), `R.valence`, `R.power`, `R.formal`,
`R.trust`, `R.debt` (Equality Matching balance) and `R.grievance`.

**Belief (`K.`)**, about an event: `K.event`, `K.source` (witness, told by whom), `K.hops`,
`K.when` (when they learned), `K.certainty`, `K.fields` (what survived levelling), `K.mag`
(after sharpening), `K.intent` (after assimilation) and `K.lied` (whether it came through a lie).

**Person (`K.`, from personality):** `K.gossip`, `K.embellish`, `K.lie`, `K.k_threshold`
(the complex-contagion k).
