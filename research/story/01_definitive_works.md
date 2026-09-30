# 1. The definitive works, read

Primary texts in the public domain were read in full or in their key chapters from local copies in
`reference/story/` (gitignored):
- Aristotle's *Poetics* (Butcher translation);
- Polti's *The Thirty-Six Dramatic Situations* (1921 English);
- Freytag's *Technique of the Drama* (1900);
- Masters's *Spoon River Anthology* (1915);
- Anderson's *Winesburg, Ohio*;
- Eliot's *Middlemarch*.

Works still in copyright were taken from their authors' own summaries and standard references
(linked). Each section ends with **what the engine takes**.

## 1.1 Aristotle, *Poetics* (c. 335 BC)
Read: chapters VI–XIV ([Gutenberg #1974](https://www.gutenberg.org/ebooks/1974)).
- **Plot first.** Plot is "the arrangement of the incidents", and "the first and most important
  thing". Character and thought are "the two natural causes from which actions spring" (VI).
- **Wholeness.** A whole has a beginning (which follows nothing by necessity), a middle and an
  end (which follows by necessity and is followed by nothing). Its length is "easily embraced by
  the memory" (VII).
- **Propter hoc, not post hoc.** Events must follow "as the necessary or probable result of the
  preceding action. It makes all the difference whether any given event is a case of propter hoc
  or post hoc" (X).
- **Reversal and recognition.** A reversal (*peripeteia*) is the action veering to its opposite.
  A recognition (*anagnorisis*) is "a change from ignorance to knowledge, producing love or hate
  between the persons". The best recognition coincides with a reversal. A third part is the
  scene of suffering (XI).
- **The best tragic character** (XIII) is neither eminently good nor villainous, but falls "not by
  vice or depravity, but by some error or frailty" (*hamartia*). A double ending, with good
  rewarded and bad punished, is "proper rather to Comedy".
- **The interpersonal core** (XIV):
  - "Actions capable of this effect must happen between persons who are either friends or enemies
    or indifferent … when the tragic incident occurs between those who are **near or dear** to one
    another … these are the situations to be looked for by the poet."
  - He then enumerates the cases: the deed **done or not done**, **knowingly or in ignorance**.
    The finest is about to act in ignorance and recognising the person in time. The worst is about
    to act knowingly and then not acting.

**What the engine takes:**
- **Story weight scales with closeness.** An arc's intensity multiplies by the tie strength between
  its parties (`R.layer`). The same harm is an anecdote between strangers and a tragedy between
  siblings.
- **Recognition is a knowledge event.** It is precisely a `K` belief arriving (04 §4 of the
  psychology research). Our propagation engine generates recognitions for free, and the drama
  manager can *time* them.
- **The Aristotle grid** is `ST.deed` (done or undone) × `ST.aware` (knowing or ignorant) on every
  harmful beat.
- **Causality is a quality test.** Beats must be linked by cause, as a chain of events, not merely
  follow one another.

## 1.2 Freytag, *Technique of the Drama* (1863; MacEwan tr. 1900)
Read: "Five parts and three crises" ([Internet Archive](https://archive.org/details/freytagstechniqu00freyuoft)).
- The drama has "a pyramidal structure. It rises from the introduction with the entrance of the
  exciting forces to the climax, and falls from here to the catastrophe."
- **Five parts:** introduction, rise, climax, return (fall) and catastrophe.
- **Three crises** between them:
  - the **exciting moment or force** ("the beginning of the stirring action"), which he calls
    necessary to every play;
  - the **tragic moment or force**, where the counter-action begins;
  - the **moment or force of the last suspense**, before the catastrophe.
  
  The second and third are "good but not indispensable".

**What the engine takes:** `ST.stage` ∈ {intro, exciting, rise, climax, tragic, fall, suspense,
resolution}. It is the drama manager's clock and the tension target for each beat.

## 1.3 Polti, *The Thirty-Six Dramatic Situations* (1895; tr. Ray 1921)
Read: all 36 headings and their required "elements" ([Internet Archive](https://archive.org/details/thirtysixdramati00polt)).
Polti takes the number from Gozzi and gives, for each situation, the **dynamic elements
technically necessary**:

| # | situation | elements (roles) |
|---|---|---|
| 1 | Supplication | a Persecutor, a Suppliant, a Power in authority whose decision is doubtful |
| 2 | Deliverance | an Unfortunate, a Threatener, a Rescuer |
| 3 | Crime pursued by vengeance | an Avenger, a Criminal |
| 4 | Vengeance taken for kindred upon kindred | Avenging Kinsman, Guilty Kinsman, remembrance of the Victim (a relative of both) |
| 5 | Pursuit | Punishment, Fugitive |
| 6 | Disaster | a Vanquished Power, a Victorious Enemy or a Messenger |
| 7 | Falling prey to cruelty or misfortune | an Unfortunate, a Master or a Misfortune |
| 8 | Revolt | Tyrant, Conspirator |
| 9 | Daring enterprise | a Bold Leader, an Object, an Adversary |
| 10 | Abduction | the Abductor, the Abducted, the Guardian |
| 11 | The enigma | Interrogator, Seeker, Problem |
| 12 | Obtaining | a Solicitor and a refusing Adversary, or an Arbitrator and opposing parties |
| 13 | Enmity of kinsmen | a Malevolent Kinsman, a Hated or reciprocally hating Kinsman |
| 14 | Rivalry of kinsmen | the Preferred Kinsman, the Rejected Kinsman, the Object |
| 15 | Murderous adultery | two Adulterers, a Betrayed Husband or Wife |
| 16 | Madness | Madman, Victim |
| 17 | Fatal imprudence | the Imprudent, the Victim or Object Lost (+ Counsellor, Instigator) |
| 18 | Involuntary crimes of love | the Lover, the Beloved, the Revealer |
| 19 | Slaying of a kinsman unrecognized | the Slayer, the Unrecognized Victim |
| 20 | Self-sacrifice for an ideal | the Hero, the Ideal, the "Creditor" or the Person or Thing Sacrificed |
| 21 | Self-sacrifice for kindred | the Hero, the Kinsman, the "Creditor" or the Person or Thing Sacrificed |
| 22 | All sacrificed for a passion | the Lover, the Object of the Fatal Passion, the Person or Thing Sacrificed |
| 23 | Necessity of sacrificing loved ones | the Hero, the Beloved Victim, the Necessity for the Sacrifice |
| 24 | Rivalry of superior and inferior | the Superior Rival, the Inferior Rival, the Object |
| 25 | Adultery | a Deceived Husband or Wife, two Adulterers |
| 26 | Crimes of love | the Lover, the Beloved |
| 27 | Discovery of the dishonor of a loved one | the Discoverer, the Guilty One |
| 28 | Obstacles to love | two Lovers, an Obstacle |
| 29 | An enemy loved | the Beloved Enemy, the Lover, the Hater |
| 30 | Ambition | an Ambitious Person, a Thing Coveted, an Adversary |
| 31 | Conflict with a god | a Mortal, an Immortal |
| 32 | Mistaken jealousy | the Jealous One, the Object of whose possession he is jealous, the Supposed Accomplice, the Cause or Author of the Mistake |
| 33 | Erroneous judgment | the Mistaken One, the Victim of the Mistake, the Cause or Author of the Mistake, the Guilty Person |
| 34 | Remorse | the Culprit, the Victim or the Sin, the Interrogator |
| 35 | Recovery of a lost one | the Seeker, the One Found |
| 36 | Loss of loved ones | a Kinsman Slain, a Kinsman Spectator, an Executioner |

- More than half of the 36 are defined **by a relationship between the parties**: kin (4, 13, 14,
  19, 21, 23, 27, 35, 36) or lovers and spouses (15, 18, 22, 25, 26, 28, 29, 32).
- Several turn on **knowledge**: 11, 19, 27, 32 and 33 are about who knows or wrongly believes
  what.

**What the engine takes:** Polti's "elements" are **casting roles**. Each situation becomes a
story type whose roles have eligibility conditions over our tokens (`R.kind`, `K`, `P`, `V`).
Some need care:
- 16 (Madness) is rewritten as *crisis and recovery*, under the depiction rules in psychology 02
  §2.4;
- 15, 19 and 26 exist in the catalogue only as rare, off-screen **backstory**, never as arcs the
  engine drives toward the player.

## 1.4 Propp, *Morphology of the Folktale* (1928; English 1958)
- From about 100 Russian wonder tales, **31 functions** always appear in the same order (any may
  be missing):
  1. absentation;
  2. interdiction;
  3. violation;
  4. reconnaissance;
  5. delivery;
  6. trickery;
  7. complicity;
  8. villainy or lack;
  9. mediation;
  10. beginning counteraction;
  11. departure;
  12. the donor's test;
  13. the hero's reaction;
  14. receipt of a magical agent;
  15. guidance;
  16. struggle;
  17. branding;
  18. victory;
  19. liquidation of the lack;
  20. return;
  21. pursuit;
  22. rescue;
  23. unrecognised arrival;
  24. unfounded claims (by a false hero);
  25. difficult task;
  26. solution;
  27. **recognition**;
  28. **exposure** (of the false hero);
  29. transfiguration;
  30. punishment;
  31. wedding.
- **Seven spheres of action:** villain, donor (provider), helper, princess (the sought-for person)
  and her father, dispatcher, hero and false hero ([overview](https://en.wikipedia.org/wiki/Vladimir_Propp)).

**What the engine takes:** Propp is the original **grammar of beats**: ordered, optional, and
defined by *function*, not by who performs it. Our beats are functions too. The *false hero* and
*exposure* map onto our lies and rumours: someone takes credit for the player's deed, and a
recognition exposes them.

## 1.5 Greimas (1966) and Todorov (1971)
- **Greimas's actantial model** has six actants in three pairs
  ([actantial model](https://en.wikipedia.org/wiki/Actantial_model)):
  - **Subject ↔ Object** (desire);
  - **Sender ↔ Receiver** (communication: who sets the goal, who benefits);
  - **Helper ↔ Opponent** (power).
- **Todorov's equilibrium**: equilibrium → disruption → recognition of the disruption → attempt to
  repair → **new equilibrium** ([equilibrium theory](https://en.wikipedia.org/wiki/Todorov%27s_narrative_theory_of_equilibrium)).

**What the engine takes:**
- Every role in every story type is tagged with its **actant** (`ST.actant`). That is what lets one
  engine run 80+ story types.
- Todorov gives each arc its start and end condition: the new equilibrium is a *changed* token
  state (a tie made or broken, an opinion reversed, a role gained).

## 1.6 Campbell (1949) and Vogler (1992)
- *The Hero with a Thousand Faces*: a **monomyth** of 17 stages in three acts, departure,
  initiation and return.
- Vogler's screenwriting condensation has 12: ordinary world, call, refusal, mentor, threshold,
  tests / allies / enemies, approach, ordeal, reward, road back, resurrection, return with the
  elixir. Its archetypes are hero, mentor, threshold guardian, herald, shapeshifter, shadow, ally
  and trickster ([hero's journey](https://en.wikipedia.org/wiki/Hero%27s_journey)).

**What the engine takes:** the **journey template** for the player's larger arcs. Its archetypes
are functions **NPCs play relative to the player**. A mentor, a threshold guardian or a
shapeshifter (someone whose loyalty is unclear) is a role an NPC is cast into by tokens: `R.power`
and trust for a mentor, grievance and low H for a shapeshifter.

## 1.7 Frye, *Anatomy of Criticism* (1957): four mythoi
- **Comedy** (spring): integration into society; its theme is *anagnorisis*, a new society
  forming.
- **Romance** (summer): adventure; its theme is *agon*.
- **Tragedy** (autumn): isolation; its theme is *pathos*, catastrophe.
- **Irony / satire** (winter): *sparagmos*, heroism absent or foredoomed.

([Anatomy of Criticism](https://en.wikipedia.org/wiki/Anatomy_of_Criticism))

**What the engine takes:** `ST.mythos` is the **outcome family** of an arc. The same rivalry can
resolve as comedy (the rivals join the community), romance (the better one triumphs), tragedy (the
rivalry destroys one of them) or irony (nobody wins). The drama manager balances the mix over the
player's history.

## 1.8 Booker, *The Seven Basic Plots* (2004); Tobias, *20 Master Plots* (1993)
- **Booker:** overcoming the monster, rags to riches, the quest, voyage and return, comedy,
  tragedy and rebirth. Each has a five-stage shape. Tragedy's is anticipation, dream, frustration,
  nightmare, destruction ([summary](https://tropedia.fandom.com/wiki/The_Seven_Basic_Plots)).
- **Tobias:** quest, adventure, pursuit, rescue, escape, revenge, the riddle, rivalry, underdog,
  temptation, metamorphosis, transformation, maturation, love, forbidden love, sacrifice,
  discovery, wretched excess, ascension, descension ([Writer's Digest](https://writersdigest.com/improve-my-writing/20-master-plots)).

**What the engine takes:** coverage checks for the catalogue (03). Every Booker and Tobias plot
maps to at least one story type.

## 1.9 Egri (1946), McKee (1997), Regis (2003): craft and a relationship genre
- **Egri, *The Art of Dramatic Writing*:**
  - a story demonstrates a **premise**, a thesis about human behaviour, such as "jealousy
    destroys itself and the object of its love";
  - character is three-dimensional: physiology, sociology, psychology;
  - conflict needs a *unity of opposites*: the parties are bound together so neither can simply
    walk away ([review](https://neiloseman.com/the-art-of-dramatic-writing-by-lajos-egri/)).
- **McKee, *Story*:** story happens in "the gap between expectation and result". Scenes turn a
  **value charge** (love/hate, trust/betrayal, freedom/slavery) from + to − or back. A scene that
  doesn't turn a value is a non-event ([gap](https://mckeestory.com/blog/page/8/?et_blog)).
- **Regis, *A Natural History of the Romance Novel*:** eight essential elements: society defined,
  meeting, **barrier**, attraction, declaration, **point of ritual death** (the barrier seems
  insurmountable), recognition, betrothal ([elements](https://careerauthors.com/how-and-why-to-add-romance-in-any-genre/)).

**What the engine takes:**
- **Unity of opposites** is an eligibility rule. Conflict arcs need parties who *can't easily leave
  each other*: the same household, workplace or settlement, a low `W.relmob`, or a shared need.
- Every beat must **turn a value** (`ST.value` with its polarity before and after).
- Regis's eight beats are the courtship template.
- Egri's premise is `ST.theme`, a sentence the dialogue can hint at.

## 1.10 Kishōtenketsu (起承転結)
- Classical Chinese and Japanese four-part structure: **ki** (introduction), **shō**
  (development), **ten** (twist) and **ketsu** (reconciliation). It needs **no conflict**: the twist
  recontextualises rather than opposes. *Spirited Away* is a common example
  ([kishōtenketsu](https://filmlifestyle.com/what-is-kishotenketsu/)).

**What the engine takes:** this is essential for a Ghibli-toned world. Quiet arcs (kindness,
craft, wonder, homesickness, an elder remembered) run on ki–shō–ten–ketsu **without a villain**.
The drama manager must be able to choose calm, as RimWorld's "Phoebe Chillax" does.

## 1.11 The shape of feeling: Reagan et al. 2016; Vonnegut
- The sentiment arcs of 1,327 Project Gutenberg novels cluster into **six basic shapes**:
  - rags to riches (rise);
  - riches to rags (fall);
  - man in a hole (fall then rise);
  - Icarus (rise then fall);
  - Cinderella (rise, fall, rise);
  - Oedipus (fall, rise, fall).
  
  ([arXiv 1606.07772](https://www.alphaxiv.org/abs/1606.07772))
- Toubia, Berger & Eliashberg (*PNAS* 2021) quantified the *speed, volume and circuitousness* of
  stories' semantic paths and linked them to success ([paper](https://faculty.wharton.upenn.edu/wp-content/uploads/2016/11/How-Quantifying-the-Shapes-of-Stories-Predicts-their-Success.pdf)).

**What the engine takes:** `ST.shape` is the target valence curve of an arc for its protagonist.
The drama manager steers beat choice toward it.

## 1.12 The folk indices: Aarne–Thompson–Uther and the Motif-Index
- The **ATU tale-type index** catalogues international tale types (found in three or more
  cultures): Animal Tales, **Tales of Magic**, Religious Tales, **Realistic Tales (novelle)**,
  Tales of the Stupid Ogre, **Anecdotes and Jokes**, and Formula Tales
  ([Harvard guide](https://guides.library.harvard.edu/folk_and_myth/indices)).
- Thompson's **Motif-Index** catalogues the motifs within them.

**What the engine takes:** the *realistic tales* and *anecdotes* are the everyday stories a town
tells about itself: the clever servant, the foolish rich man, the faithful wife tested, the
returned soldier. They feed the **gossip-sized** story types (03, family G), and later the
literary research.

## 1.13 The interpersonal canon: stories of a web of people
Chosen because a town simulation *is* a web of lives.
- **Masters, *Spoon River Anthology* (1915)**, read and analysed ([Gutenberg #1280](https://www.gutenberg.org/ebooks/1280)).
  - It holds 242 epitaphs by the dead of one small town.
  - **41% of speakers name another resident.** The most-named are the town's **role-holders**:
    the banker Thomas Rhodes (13 other speakers mention him), the Circuit Judge (9), the town drunk
    Chase Henry (7), Judge Somers, the Reverend Abner Peet and Editor Whedon.
  - **23 families** have several speakers.
  - Recurring words: love (37 poems), children (36), father (28), village (25), **truth (24)**,
    wife (23), **lie (19)**, church (19), married (17), **secret (13)**.
  - The Pantiers show one marriage from both sides. The husband says his wife "snared my soul";
    she answers, *"I know that he told that I snared his soul … And all the men loved him, / And
    most of the women pitied him"*, and gives her reasons. Their son Reuben says "I pass the
    effect of my father and mother", and credits his old teacher, Emily Sparks, with saving him.
    She, in her own poem, never learned how he turned out ("Where is my boy?").
  - **Lessons, which the engine already implements:**
    1. The same event carries **opposed appraisals** by different people (OCC + values).
    2. People **know what is said about them** (propagation reaching the subject).
    3. The **town's verdict** (who loved him, who pitied him) is an aggregate of individual
       opinions.
    4. Effects **radiate one degree to kin**.
    5. **Role-holders are narrative hubs.** This is support for the salience-by-prominence rule and
       the next research round.
    6. **Dramatic irony** comes from knowledge gaps (Emily never learns).
- **Anderson, *Winesburg, Ohio* (1919)**: linked stories of one town's "grotesques", people
  bent by a single truth they clung to. The recurring figure is a young reporter, George Willard,
  to whom they confide. It is the model of **a newcomer or witness who hears the town's stories**,
  which is the player's position.
- **Eliot, *Middlemarch* (1871–72)**: the novel of a provincial town as an **interlocking web**.
  Its finale ends: "the growing good of the world is partly dependent on unhistoric acts". Small
  kindnesses ripple, so the *quiet* arcs matter.
- **Shakespeare's relational tragedies:**
  - *King Lear*: family, loyalty tested, a misjudged love (Polti 33);
  - *Othello*: mistaken jealousy engineered by a false friend (Polti 32);
  - *Romeo and Juliet*: an enemy loved, a feud, a misdelivered message (Polti 29, plus a
    knowledge failure).
  
  The canon's great relationship stories are nearly all **knowledge stories**: who knows, who is
  lied to, who learns too late.

## 1.14 Stories in systems: the game and AI side
- **Façade** (Mateas & Stern 2005). A **drama manager** sequences authored beats from a pool, so
  that tension rises and falls along an Aristotelian arc. Beats have preconditions over story
  memory ([Façade architecture](https://www.cs.uky.edu/~sgware/reading/papers/mateas2005structuring.pdf)).
- **Storylets and quality-based narrative** (Failbetter; Emily Short):
  - storylets are small content units unlocked by **qualities**; "the qualities *are* the world
    state";
  - **salience-based** narrative picks the most applicable item from a pool;
  - **waypoint** narrative steers conversation toward goals
  
  ([Beyond branching](https://emshort.blog/2016/04/12/beyond-branching-quality-based-and-salience-based-narrative-structures/)).
- **RimWorld's storytellers** (Tynan Sylvester). The event generator analyses the colony and picks
  "the most interesting narrative". *Cassandra Classic* rises and falls in tension, *Phoebe
  Chillax* leaves long quiet stretches, *Randy Random* is chaotic ([RimWorld](https://en.wikipedia.org/wiki/RimWorld)).
- **Curating simulated storyworlds** (Ryan 2018). Emergent narrative needs **curation**: *story
  sifters* pick compelling chains of causality out of a simulation's chronicle ([dissertation](https://escholarship.org/uc/item/1340j5h2)).
  Felt and Winnow run the sifting patterns incrementally (psychology 05 §5.6).

**What the engine takes:** arcs are **storylets with state**. They are detected by sifting, cast by
eligibility and advanced by a drama manager that paces tension like a storyteller. Details are in
04.
