# 5. Roles in the engine

Roles fill the slot the psychology framework left open (`W.role*`, psychology 06 §9) and the
story layer's casting (story 04 §2). A person's roles decide:
- what they **do**: the event verbs of their duties;
- whom they **deal with**: the role set adds ties;
- what they **know without being told**: knowledge channels;
- how far their acts **spread**: prominence becomes salience;
- how they are **named and judged**: master status and prestige;
- which **stories** they can be cast in: hooks.

## 1. Role tokens (`RL.`)
| token | meaning | from |
|---|---|---|
| `RL.primary` | main work role (catalogue id) | the occupation draw (extends the existing `occupation` trait) |
| `RL.household` | household and kin roles: parent, caregiver, kin-keeper, … | the households generator |
| `RL.civic` | civic and institutional roles held (0–3; "joiners" hold several) | per-settlement allocation |
| `RL.informal` | emergent roles: clown, broker, gossip, confidant, … | computed from tokens and network position (§3) |
| `RL.status` | station status: founder, born here, recent arrival, contract worker | `C.origin` |
| `RL.master` | the role others lead with ("the doctor", "the newcomer", "the drunk") | the highest prominence × visibility |
| `RL.prestige` | 1–5 | catalogue (NORC/GSS anchors) |
| `RL.prominence` | 0–1: salience multiplier for this person's events, and their pull as a story hub | catalogue, and informal roles |
| `RL.class` | business, working or none (Middletown; McMurdo's science/support divide) | catalogue |
| `RL.knows` | privileged knowledge channels | catalogue |
| `RL.set` | the role set (whom it deals with) | catalogue |
| `RL.strain` | strain from overload or conflict between roles; adds to `S.stress` | the count and combination of roles (Goode) |
| `W.roles` | the roles this settlement needs, and how many (frequencies × size, and essential systems) | catalogue × settlement record |
| `W.vacant` | critical roles vacant or contested (formal: no doctor, one air-plant operator; informal: no clown, no heart leader) | allocation (§2–3) |
| `W.cohesion` | the share of critical informal roles filled by consensus | §3 |

## 2. Allocation: who holds which role
1. **Settlement needs** (`W.roles`), from the catalogue:
   - per-1,000 frequencies × population for work roles, with station essential-systems roles as
     **minimums** (at least one air-plant operator per settlement, and so on);
   - per-settlement counts for civic roles;
   - shaped by the settlement's type and founding economy (psychology 03: `W.org`, `W.legacy`).
2. **Filling.** Each residence's adults draw work roles by weight, subject to eligibility (age,
   traits, class homophily with household). This is deterministic from the seed, like every other
   trait.
3. **Many hats.** In small settlements the essential roles outnumber qualified people, so some
   adults hold two. That raises strain and prominence ("the doctor is also the coroner"). This is
   one of SP-413's observations about small colonies.
4. **Civic roles** go to "joiners" (high E and C, founders and long-timers first, Gans), often
   stacked on the same people (Putnam).
5. **Vacancies** (`W.vacant`) are left open when nobody eligible exists. They are **story hooks**:
   the settlement needs a doctor; nobody runs the festival any more.

## 3. Informal roles emerge, and cohesion follows
- **Computing informal roles.** Informal roles are not drawn; they are **computed** from tokens and
  **network position** in the settlement graph (psychology 06 §4.1). The groups are found by label
  propagation over work, neighbour and club ties. Examples:
  - **clown**: humour × E × number of groups spanned;
  - **heart leader**: communion × A × centrality;
  - **task leader**: agency × C × centrality;
  - **peacemaker**: A × H × groups spanned;
  - **confidant**: A × discretion × centrality;
  - **broker**: the top 5% by groups spanned;
  - **gossip**: `K.gossip` × degree;
  - **loner**: few ties.
- **Consensus matters** (Johnson, Boster & Palinkas 2003). A critical role counts as filled only if
  one candidate clearly stands out. Two close candidates make the role **contested**, which is
  itself a rivalry hook.
- **`W.cohesion`** is the share of critical informal roles filled: task leader, heart leader,
  clown, peacemaker and confidant.
- **Low cohesion means a clique structure.** The settlement's groups gather around their leisure
  places, as the South Pole's Biomed, Library and Bar cliques did, and the effects are:
  - more `S.stress` for everyone (Palinkas: clique crews had more depression, anxiety, anger and
    fatigue);
  - more feud, rivalry and scapegoat arcs;
  - propagation stays inside cliques (fewer bridges).
- **High cohesion means a core–periphery structure:** calmer, with news crossing groups and
  quieter arcs.
- **The player can fill a vacancy.** Being the one who jokes across the divide, mediates the feud,
  or takes charge in the crisis earns the role's prominence, a place in the settlement's stories
  and, over time, the role as `RL.master` in others' beliefs.
- **The prototype** (`tools/story/roles_proto.py`), over 8 generated settlements of 300:
  - each has 11–16 cliques of about 20 people (work, street, clubs);
  - cohesion ranges from **0.6 to 1.0**;
  - vacancies were usually **contested** rather than empty: two near-equal candidates;
  - brokers were 4–13% of adults, gossips 1–5 per settlement, loners 6–15.
  
  The mechanic produces varied, plausible towns, each with its own gaps.

## 4. Roles feed every other layer
| layer | how roles act on it |
|---|---|
| **ties** (psychology 06 §4.1) | a role set adds edges (a doctor's patients, a teacher's pupils' parents, the postal carrier's route) with the right relational model (AR for official roles, MP for trade, CS for kin roles) |
| **knowledge** (06 §4) | knowledge channels are **extra witnesses**: the doctor learns of injuries and births, the bartender of what was said drunk, the comms officer of Earth news, the clerk of debts. These are separate from word of mouth, and bound by the role's discretion (a doctor's confidentiality lowers their `K.gossip` for health facts) |
| **propagation** | `RL.prominence` multiplies salience. The mayor's misdeed, the doctor's kindness and the drunk's brawl travel further. **Opinion leaders** and **editors** are the public channel's entry points; **brokers** carry news between groups; **drivers and pilots** carry it between settlements |
| **appraisal** (06 §5) | **role expectations are standards**. A doctor who breaks confidence, a marshal who steals or a teacher who lies violates their role, and reproach is multiplied by prestige (the higher the seat, the harder the fall: `downfall`). A role also sets the **relational model** each act is judged under |
| **stress** | `RL.strain` (overload, conflict) adds to `S.stress`. Roles held against one's traits (a shy person as a shopkeeper) add strain; fitting roles lower it |
| **stories** (story 04) | hooks make role-holders **eligible casts**: the marshal pursues, the pastor hears remorse, the editor spreads the rumour, the administrator is the scapegoat target. Vacancies and contested roles are **arc triggers** (`election`, `rivalry`, `ambition`, `stranger_arrives` for the player filling a gap) |
| **dialogue** (06 §8) | the `[PERSON]` line leads with `RL.master`, and duties set what they talk about and how. The `[STORY]` section already carries their cast role |
| **schedule and placement** | work roles set where people are, when (existing `schedule`), and which foci they belong to |

## 5. Build plan
1. Load `roles.json`; derive `W.roles` per settlement; allocate work, civic and household roles
   deterministically (extending `NpcTraits` and `NpcHouseholds`).
2. Add role-set ties and knowledge channels to the settlement graph and the knowledge query.
3. Compute informal roles and `W.cohesion` per settlement (ported from `roles_proto.py`), cached
   with the graph.
4. Prominence into salience; role standards into appraisal; strain into stress.
5. Vacancies and contested roles as sifting triggers; player-held informal roles.
6. Tests: allocation frequencies against the catalogue, determinism, cohesion distribution.
