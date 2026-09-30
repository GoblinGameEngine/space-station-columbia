# 1. Role theory: what a role is, and what it does to a person

A **role** is the bundle of expected behaviour attached to a position. It shapes what a person
does, whom they deal with, what they know, how they are judged, and which stories they can be in.
The classic concepts, and how each becomes tokens (prefix `RL.`, catalogue in 04):

| concept | source | what it says | engine |
|---|---|---|---|
| **Status and role; ascribed and achieved** | Linton, *The Study of Man* (1936) | a *status* is a position; a *role* is its dynamic side, the behaviour expected of it. Some statuses are **ascribed** (born into: child, sibling, founder's grandchild), others **achieved** (doctor, mayor) | `RL.kind` ∈ ascribed, achieved, emergent (informal roles, below) |
| **Role set and status set** | Merton (1957) ([role set](https://en.wikipedia.org/wiki/Role_set)) | a single status involves a *role set*, "the complement of social relationships in which persons are involved because they occupy a particular social status": a doctor's colleagues, nurses, patients, administrators | `RL.set` lists who a role deals with. It **adds ties** to the settlement graph (psychology 06 §4.1) and gives `R.model` (patient–doctor is AR/MP) |
| **Role strain** | Goode (1960) ([summary](https://www.simplypsychology.org/what-is-role-strain-in-sociology.html)) | friction from incompatible demands *within* one role: overload, conflict, incongruity, ambiguity. *Role conflict* is between two roles, such as parent and night-shift nurse | `RL.strain`: adds to `S.stress`; source of story (`hard_choice`, `divided_loyalty`) |
| **Master status** | Hughes (1945) ([master status](https://en.wikipedia.org/wiki/Master_status)) | one status dominates how others see a person, whatever else they are | `RL.master`: the role that others' beliefs **lead with** ("the doctor", "the newcomer", "the drunk"). Prompts name people by it |
| **Instrumental and expressive leadership** | Bales (1950); Parsons; Johnson, Boster & Palinkas (2003) | groups need a **task (instrumental) leader** and a **socio-emotional (expressive) leader**, usually different people | informal roles `leader_task`, `leader_heart` (04 family F) |
| **Opinion leaders: the two-step flow** | Katz & Lazarsfeld, *Personal Influence* (1955) ([summary](https://aura-lab.siue.edu/theories/two-step-flow/)) | media reach **opinion leaders**, who pass it on by talk; personal contact swayed voters more than radio or print | `opinion_leader`: a high-salience hub for the **public channel** (psychology 06 §4.2). News reaches most people through them |
| **Brokers and structural holes** | Burt (1992) ([Burt](https://en.wikipedia.org/wiki/Ronald_Stuart_Burt)) | whoever spans a gap between groups controls what flows across it | `broker`: computed from network position (bridging ties). Their `K.gossip` gates cross-group spread |
| **Kin work** | di Leonardo (1987) ([Signs](https://www.journals.uchicago.edu/doi/10.1086/494338)) | "the conception, maintenance, and ritual celebration of cross-household kin ties": visits, calls, cards, holidays. Unacknowledged work, culturally assigned to women | `kinkeeper`: keeps kin ties across households from decaying (psychology 04 §4.1). Their absence lets a family drift (`estrangement`) |
| **Public characters and eyes on the street** | Jacobs (1961); Duneier, *Sidewalk* (1999) ([Death and Life](https://en.wikipedia.org/wiki/The_Death_and_Life_of_Great_American_Cities)) | shopkeepers and street regulars who know many people and are known by them; their watching keeps streets safe | `public_character`: **witness coverage**. Their presence raises the chance a public event is seen (06 §3) |
| **Third places and regulars** | Oldenburg, *The Great Good Place* (1989) ([third place](https://en.wikipedia.org/wiki/Third_place)) | neutral, levelling, conversational places (bar, café, barbershop) that "draw a base of regulars that sets the tone" | `regular` plus the third-place **host** (bartender, barber). Hosts are gossip hubs, and third places are foci with high tie probability |
| **Institutions broker ties** | Small, *Unanticipated Gains* (2009); Klinenberg, *Palaces for the People* (2018) ([Small](https://mariosmall.com/unanticipated-gains)) | the routines of childcare centres, churches, libraries and gyms create ties more than deliberate networking does | the role-holders who run institutions (teacher, librarian, pastor, childcare worker) raise the **tie probability of their focus** |

**Two things matter most for the engine:**
1. **Roles are ties.** A role's set adds edges and relational models to the social graph. The
   doctor knows the sick; the postal worker has passed everyone's door.
2. **Roles are channels.** Role-holders have privileged **knowledge access**: the doctor knows who
   is ill, the bartender hears what people say drunk, the clerk knows who owes. Prominent roles
   are **salient**, so what they do spreads further. In *Spoon River*, the banker, the judges,
   the preacher and the editor are the most-discussed people in town (story 01 §1.13).
