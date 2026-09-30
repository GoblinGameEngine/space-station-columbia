# 2. What makes a good story, as rules the engine can check

Each principle below comes with its evidence or authority and a **test** the engine can compute
over an arc instance. Together the tests form `ST.quality`. The drama manager and the story sifter
use it to pick which of the many things happening in the world to develop, and which to let pass.

## 2.1 Evidence from psychology
| principle | evidence | engine test |
|---|---|---|
| **Causality holds a story together** | Story events with more causal connections are better recalled and judged more important (Trabasso & van den Broek 1985); Aristotle's *propter hoc*, not *post hoc* ([summary](https://arxiv.org/pdf/2311.09648)) | `causal_density`: the share of the arc's beats caused by an earlier beat, where an event's actor had a belief (K) about the earlier event, or a grievance or need from it. Arcs whose beats merely follow one another are dropped. |
| **Stories run on suspense, surprise and curiosity** | Brewer & Lichtenstein's structural-affect theory: *suspense* (the reader knows a threat, and the outcome is uncertain), *surprise* (information withheld and then revealed), *curiosity* (a known outcome with an unknown cause) ([Brewer & Lichtenstein via review](https://www.moviemaker.com/first-draft-psychological-states/)) | Each beat is tagged with the affect it serves. **Suspense** needs the player to know a threat an NPC doesn't: K asymmetry. **Surprise** is a recognition the player couldn't have predicted from what they knew. **Curiosity** is an event whose cause (actor or intent) is unknown to the player. |
| **Transportation drives engagement and change** | Being "transported" into a narrative, an integrative melding of attention, imagery and feeling, is the mechanism by which stories persuade (Green & Brock 2000) ([review](https://thejuryexpert.com/2011/05/narrative-persuasion/)) | Continuity of cast (the same few people recur), concrete sensory detail in dialogue (a prompt instruction), and no abrupt tonal breaks: the drama manager limits mythos switches. |
| **Fiction simulates social life** | Narrative fiction abstracts, simplifies and compresses social experience, and improves the understanding of others (Mar & Oatley 2008) ([paper](https://lchc.ucsd.edu/MCA/Mail/xmcamail.2010_01.dir/pdfc8vBXO7Maa.pdf)) | Arcs must turn on **other minds**: a belief, an intention or a feeling revealed. A good arc contains at least one theory-of-mind beat, where someone learns what another thought or felt. |
| **Emotional shape matters** | Six basic arcs account for most stories (Reagan et al. 2016). Semantic speed, volume and circuitousness predict success (Toubia et al. 2021) | Track the protagonist's valence per beat. Prefer arcs whose curve fits a named shape. Avoid flat stretches: 3 beats without a value turn is a stall. |
| **Bad is stronger than good** | Negative events and impressions weigh more (Baumeister et al. 2001) | Balance: a player history needs about three positive beats for every negative one to feel even. The drama manager counts them. |

## 2.2 Authority from craft and theory
| principle | source | engine test |
|---|---|---|
| **Closeness makes it matter** | Aristotle XIV: deeds "between those who are near or dear" | `intensity` = the arc's stakes × tie strength between its principal parties. Arcs between strangers are anecdotes; between kin, drama. |
| **Recognition and reversal** | Aristotle X–XI; Todorov's recognition stage; Propp 27–28 | A good arc has a **recognition** (a K event for a principal) and a **reversal** (a value turning from + to − or − to +), ideally in the same beat. |
| **Flawed, not wicked** | Aristotle XIII (*hamartia*) | Principal antagonists come from mid-range people with one extreme (a `D.*` facet, an honor culture, a grievance), not from pure villains. Pure-villain arcs are capped. |
| **Every scene turns a value** | McKee | Each beat declares `ST.value` and its polarity before and after. A beat that changes nothing is not played. |
| **Unity of opposites** | Egri | Conflict arcs need parties who can't easily leave: the same household, workplace or settlement, a low `W.relmob`, dependence (`R.power`) or a debt. Otherwise the arc dissolves: someone just avoids the other. That is realistic too. |
| **A premise** | Egri | `ST.theme` is a short thesis; the dialogue may echo it, never state it. |
| **The exciting force is required** | Freytag | An arc starts only from an inciting **event** (from the log), never from nothing. |
| **Setup and payoff** | Chekhov's gun (Chekhov's letters, 1889); Propp's interdiction then violation | Beats may plant a **promise token** (a threat, a vow, a secret, an object) that a later beat must pay off, or the arc loses quality. |
| **Agency** | Game design (Façade, storylets) | The player can act at every beat that involves them, and their action changes the next beat. Beats offer **affordances**, as Versu's social practices do. |
| **Variety and rest** | RimWorld storytellers; SP-413's "variety prevents stress"; kishōtenketsu | The drama manager alternates tension with quiet arcs, and conflict with non-conflict (ki–shō–ten–ketsu). |
| **Endings that change the world** | Todorov's new equilibrium; Frye's mythoi | Resolution beats must write a lasting **delta**: a tie changed, opinions changed, a role gained or lost, a belief spread. The world remembers. |

## 2.3 The quality score
```
ST.quality = intensity(closeness × stakes)
           × causal_density
           × (1 + recognition + reversal)          -- Aristotle's complex plot
           × affect_fit(suspense|surprise|curiosity available now)
           × shape_fit(valence curve vs chosen ST.shape)
           × payoff_ratio(promises paid / planted)
           × novelty(not the same type as the player's last 3 arcs)
```
- The **story sifter** uses it to rank candidate arcs detected in the event log.
- The **drama manager** uses it to choose which live arc to advance, and which beat.
- It is always tempered by the storyteller's pacing target (04 §5).
